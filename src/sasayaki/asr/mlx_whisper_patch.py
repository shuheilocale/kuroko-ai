"""Monkey-patch mlx-whisper's MultiHeadAttention to use MLX's fused
scaled dot-product attention (the Apple Silicon equivalent of
FlashAttention).

The reference mlx-whisper implementation materialises the full
QK^T attention matrix and runs softmax on it. mx.fast.scaled_dot_product_attention
fuses the same computation into a single Metal kernel — mathematically
equivalent (no accuracy loss), but ~10–20% faster and lower memory.

Safe to apply unconditionally because we never request
word_timestamps; the original method's `qk` return value (used only
for DTW timestamp alignment) is replaced with None.
"""
from __future__ import annotations

import logging

import mlx.core as mx

logger = logging.getLogger(__name__)

_PATCHED = False


def _qkv_attention_sdpa(self, q, k, v, mask=None):
    n_batch, n_ctx, n_state = q.shape
    n_head = self.n_head
    head_dim = n_state // n_head
    scale = head_dim**-0.5

    # SDPA expects [B, H, T, D] for both Q and K (no pre-transpose of K).
    q = q.reshape(n_batch, n_ctx, n_head, head_dim).transpose(0, 2, 1, 3)
    k = k.reshape(*k.shape[:2], n_head, head_dim).transpose(0, 2, 1, 3)
    v = v.reshape(*v.shape[:2], n_head, head_dim).transpose(0, 2, 1, 3)

    sdpa_mask = mask[:n_ctx, :n_ctx] if mask is not None else None
    out = mx.fast.scaled_dot_product_attention(
        q, k, v, scale=scale, mask=sdpa_mask
    )
    out = out.transpose(0, 2, 1, 3).reshape(n_batch, n_ctx, n_state)
    # Original returned `qk` for DTW token-timestamps; we don't use them.
    return out, None


def apply() -> None:
    """Install the SDPA-backed attention. Idempotent."""
    global _PATCHED
    if _PATCHED:
        return
    from mlx_whisper.whisper import MultiHeadAttention

    MultiHeadAttention.qkv_attention = _qkv_attention_sdpa
    _PATCHED = True
    logger.info(
        "mlx-whisper: patched MultiHeadAttention.qkv_attention -> "
        "mx.fast.scaled_dot_product_attention"
    )
