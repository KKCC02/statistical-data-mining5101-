"""Pairwise logistic design for nested Bradley-Terry extensions.

Every row is one A/B response. The linear predictor is the sum of per-block
contrasts between side A and side B, so leaving a block out of ``blocks`` is
exactly the restriction that drops its term from the model:

* ``cat``       cat ability difference ``u_catA - u_catB`` (the BT baseline),
* ``image``     image effect difference ``v_imageA - v_imageB``,
* ``side``      a single A-side intercept (presentation position),
* ``group``     respondent-attribute main effect on the A-side intercept,
* ``group_cat`` respondent group by cat ability interaction.

Contrasts are shift invariant: adding a constant to every level of a difference
block leaves each A-versus-B contrast unchanged. One level per block is therefore
dropped as a reference for fitting (one per group for ``group_cat``), and the
reported effects are centred so that each identified unit sums to zero. Neither
step changes a fitted contrast.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.optimize import minimize
from scipy.special import expit

from cat_arena.common.paths import CONFIG

DIFFERENCE_BLOCKS = ('cat', 'image', 'group_cat')
ROW_BLOCKS = ('side', 'group')
BLOCKS = DIFFERENCE_BLOCKS+ROW_BLOCKS
GROUP_FIELD = 'pet_history'
MISSING_LEVEL = 'missing'


def _labels(frame, field):
    return frame[field].astype('string').fillna(MISSING_LEVEL).to_numpy()


def block_levels(frame, block):
    """Sorted level labels for a block, taken only from the passed frame."""
    if block == 'cat':
        return np.unique(np.concatenate([frame.a_cat.to_numpy(), frame.b_cat.to_numpy()]))
    if block == 'image':
        return np.unique(np.concatenate([frame.a_image.to_numpy(), frame.b_image.to_numpy()]))
    if block == 'side':
        return np.array(['A'])
    if block == 'group':
        return np.unique(_labels(frame, GROUP_FIELD))
    if block == 'group_cat':
        cats, groups = block_levels(frame, 'cat'), block_levels(frame, 'group')
        return np.array([f'{g}|{c}' for g in groups for c in cats], dtype=object)
    raise ValueError(f'Unknown block: {block}')


def _positions(values, levels):
    return pd.Index(levels).get_indexer(pd.Index(values))


def _entries(frame, block, levels):
    """Level positions touched by each row; the second half of a difference block is side B."""
    rows = np.arange(len(frame))
    if block == 'side':
        return rows, np.zeros(len(frame), dtype=int)
    if block in ('cat', 'image'):
        fields = ('a_cat', 'b_cat') if block == 'cat' else ('a_image', 'b_image')
        return (np.concatenate([rows, rows]),
                np.concatenate([_positions(frame[fields[0]].to_numpy(), levels[block]),
                                _positions(frame[fields[1]].to_numpy(), levels[block])]))
    if block == 'group':
        return rows, _positions(_labels(frame, GROUP_FIELD), levels[block])
    if block == 'group_cat':
        n_cats = len(levels['cat'])
        groups = _positions(_labels(frame, GROUP_FIELD), levels['group'])
        return (np.concatenate([rows, rows]),
                np.concatenate([groups*n_cats+_positions(frame.a_cat.to_numpy(), levels['cat']),
                                groups*n_cats+_positions(frame.b_cat.to_numpy(), levels['cat'])]))
    raise ValueError(f'Unknown block: {block}')


def _signs(frame, block):
    size = 2*len(frame) if block in DIFFERENCE_BLOCKS else len(frame)
    sign = np.ones(size)
    if block in DIFFERENCE_BLOCKS:
        sign[len(frame):] = -1.0
    return sign


def _free_mask(block, levels):
    """Which levels carry a free parameter; the dropped ones are references."""
    mask = np.ones(len(levels[block]), dtype=bool)
    if block == 'side':
        return mask
    if block == 'group_cat':
        mask[::len(levels['cat'])] = False
    else:
        mask[0] = False
    return mask


def _block_parts(frame, blocks, levels, strict=False):
    """(rows, free column, sign) per block, plus the total free width."""
    parts, width = [], 0
    for block in blocks:
        if block not in BLOCKS:
            raise ValueError(f'Unknown block: {block}')
        rows, position = _entries(frame, block, levels)
        if strict and (position < 0).any():
            raise ValueError(f'Unseen {block} level while fitting')
        mask = _free_mask(block, levels)
        keep = mask[position] & (position >= 0)
        column = np.cumsum(mask)-1
        parts.append((rows[keep], column[position[keep]]+width, _signs(frame, block)[keep]))
        width += int(mask.sum())
    return parts, width


def build_design(frame, blocks, levels):
    """Sparse design matrix and +1/-1 outcome code for the requested blocks."""
    parts, width = _block_parts(frame, blocks, levels, strict=True)
    matrix = sparse.coo_matrix(
        (np.concatenate([sign for _, _, sign in parts]),
         (np.concatenate([row for row, _, _ in parts]),
          np.concatenate([column for _, column, _ in parts]))),
        shape=(len(frame), width)).tocsr()
    return matrix, outcome(frame)


def outcome(frame):
    """+1 when side A was chosen, -1 when side B was chosen."""
    choice = frame.choice.to_numpy()
    if not np.isin(choice, ['A', 'B']).all():
        raise ValueError('choice must contain only A and B')
    return np.where(choice == 'A', 1.0, -1.0)


def _widths(blocks, levels):
    return {block: int(_free_mask(block, levels).sum()) for block in blocks}


def _penalty(blocks, levels, penalties):
    unknown = set(penalties)-set(blocks)
    if unknown:
        raise ValueError(f'Penalties given for unused blocks: {sorted(unknown)}')
    widths = _widths(blocks, levels)
    vector = np.concatenate([np.full(widths[b], float(penalties.get(b, 0.0))) for b in blocks]
                            ) if blocks else np.zeros(0)
    if (vector < 0).any():
        raise ValueError('Penalties must be nonnegative')
    return vector


@dataclass
class PairwiseFit:
    """Fitted contrasts plus the training-only level mapping used to build them."""

    blocks: tuple
    levels: dict
    coefficient: np.ndarray
    penalty: np.ndarray
    diagnostics: dict

    def linear_predictor(self, frame):
        """Contrast per row; levels absent from training contribute zero."""
        parts, _ = _block_parts(frame, self.blocks, self.levels)
        values = np.zeros(len(frame))
        for row, column, sign in parts:
            values += np.bincount(row, weights=sign*self.coefficient[column],
                                  minlength=len(frame))
        return values

    def predict_proba(self, frame):
        return expit(self.linear_predictor(frame))

    def unseen_coverage(self, frame):
        """Share of rows whose every referenced level was present in training."""
        covered = np.ones(len(frame), dtype=bool)
        for block in self.blocks:
            rows, position = _entries(frame, block, self.levels)
            missing = position < 0
            if missing.any():
                covered[rows[missing]] = False
        return float(covered.mean())

    def effects(self, block):
        """Centred effect per level; each identified unit sums to zero."""
        if block not in self.blocks:
            raise ValueError(f'Block {block} is not part of this model')
        mask = _free_mask(block, self.levels)
        full = np.zeros(len(mask))
        full[mask] = self.coefficient[_column_slice(self.blocks, self.levels, block)]
        if block == 'group_cat':
            group = np.repeat(np.arange(len(full)//len(self.levels['cat'])),
                              len(self.levels['cat']))
        else:
            group = np.zeros(len(mask), dtype=int)
        if block in DIFFERENCE_BLOCKS:
            for unit in np.unique(group):
                selection = group == unit
                full[selection] -= full[selection].mean()
        return pd.DataFrame({'level': self.levels[block], 'effect': full})

    def cat_scores(self):
        scores = self.effects('cat').rename(columns={'level': 'cat_id', 'effect': 'score'})
        scores['rank'] = scores.score.rank(method='min', ascending=False).astype(int)
        return scores.sort_values(['rank', 'cat_id']).reset_index(drop=True)


def _column_slice(blocks, levels, block):
    widths = _widths(blocks, levels)
    start = sum(widths[b] for b in blocks[:blocks.index(block)])
    return slice(start, start+widths[block])


def fit(frame, blocks, penalties=None):
    """Fit the pairwise logit on the passed records only."""
    blocks = tuple(blocks)
    if not blocks:
        raise ValueError('At least one block is required')
    if 'group_cat' in blocks and 'group' not in blocks:
        raise ValueError('group_cat requires the group block as well')
    penalties = penalties or {}
    levels = {block: block_levels(frame, block) for block in blocks}
    x, y = build_design(frame, blocks, levels)
    penalty = _penalty(blocks, levels, penalties)

    def objective(weight):
        margin = y*(x@weight)
        loss = np.logaddexp(0, -margin).mean()+penalty@(weight**2)
        gradient = -(x.T@(y*expit(-margin)))/x.shape[0]+2*penalty*weight
        return loss, np.asarray(gradient).ravel()

    options = dict(CONFIG['cat_ranking'])
    result = minimize(objective, np.zeros(x.shape[1]), jac=True, method='L-BFGS-B',
                      options=options)
    restarted = False
    # Large L2 candidates can exhaust the shared BT budget on a different BLAS
    # implementation. Continue the same objective from the current coefficients,
    # retaining the original ftol/gtol; never accept an unconverged fit.
    if not result.success and result.status == 1 and np.isfinite(result.x).all():
        options.update(maxiter=max(options['maxiter'], 20000), maxfun=100000, maxcor=50)
        result = minimize(objective, result.x, jac=True, method='L-BFGS-B', options=options)
        restarted = True
    if not result.success or not np.isfinite(result.x).all():
        raise RuntimeError(f'Pairwise logit optimization failed: {result.message}; '
                           f'blocks={blocks}, penalties={penalties}, iterations={result.nit}')
    diagnostics = dict(converged=True, optimizer_message=str(result.message),
                       objective=float(result.fun), records=int(len(frame)),
                       parameters=int(x.shape[1]),
                       penalized_parameters=int((penalty > 0).sum()),
                       max_abs_gradient=float(np.abs(result.jac).max()),
                       blocks=list(blocks), restarted_after_budget=restarted,
                       optimizer_options=options)
    return PairwiseFit(blocks, levels, result.x, penalty, diagnostics)
