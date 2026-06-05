"""Deep-learning sequence models for the ML Lab — LSTM & Transformer (PyTorch).

These consume a window of the last L days of features to predict h-day-forward
rainfall. Evaluated on a single chronological holdout (last 15%) — noted in the
UI — rather than k-fold CV, to keep training time bounded on CPU.
"""
from __future__ import annotations

import numpy as np

L = 21          # input window length (days)
EPOCHS = 20
BATCH = 512
HIDDEN = 32

DL_MODELS = ["lstm", "transformer"]


def torch_available() -> bool:
    try:
        import torch  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def _build_sequences(X: np.ndarray, y_all: np.ndarray):
    n = len(X)
    seqs, ys, idxs = [], [], []
    for i in range(L - 1, n):
        if np.isnan(y_all[i]):
            continue
        seqs.append(X[i - L + 1 : i + 1])
        ys.append(y_all[i])
        idxs.append(i)
    if not seqs:
        return None
    return np.asarray(seqs, dtype=np.float32), np.asarray(ys, dtype=np.float32), np.asarray(idxs)


def _make_model(kind: str, k: int):
    import torch.nn as nn

    class LSTMNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.lstm = nn.LSTM(k, HIDDEN, batch_first=True)
            self.head = nn.Sequential(nn.Linear(HIDDEN, 32), nn.ReLU(), nn.Linear(32, 1))

        def forward(self, x):
            out, _ = self.lstm(x)
            return self.head(out[:, -1, :]).squeeze(-1)

    class TransformerNet(nn.Module):
        def __init__(self):
            super().__init__()
            self.proj = nn.Linear(k, HIDDEN)
            layer = nn.TransformerEncoderLayer(HIDDEN, nhead=4, dim_feedforward=64,
                                               batch_first=True, dropout=0.1)
            self.enc = nn.TransformerEncoder(layer, num_layers=2)
            self.head = nn.Sequential(nn.Linear(HIDDEN, 32), nn.ReLU(), nn.Linear(32, 1))

        def forward(self, x):
            h = self.enc(self.proj(x))
            return self.head(h[:, -1, :]).squeeze(-1)

    return LSTMNet() if kind == "lstm" else TransformerNet()


def _standardize(train: np.ndarray, *others):
    mu = train.reshape(-1, train.shape[-1]).mean(0)
    sd = train.reshape(-1, train.shape[-1]).std(0) + 1e-6
    return [(a - mu) / sd for a in (train, *others)]


def _train(kind: str, Xtr, ytr):
    import torch
    from torch import nn, optim

    torch.manual_seed(42)
    model = _make_model(kind, Xtr.shape[-1])
    opt = optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.SmoothL1Loss()
    Xt = torch.tensor(Xtr); yt = torch.tensor(ytr)
    n = len(Xt)
    model.train()
    for _ in range(EPOCHS):
        perm = torch.randperm(n)
        for s in range(0, n, BATCH):
            idx = perm[s : s + BATCH]
            opt.zero_grad()
            loss = loss_fn(model(Xt[idx]), yt[idx])
            loss.backward()
            opt.step()
    model.eval()
    return model


def _predict(model, X):
    import torch
    with torch.no_grad():
        return model(torch.tensor(X)).numpy()


def eval_holdout(kind: str, X: np.ndarray, y_all: np.ndarray, metric_fn, ref: float) -> dict | None:
    built = _build_sequences(X, y_all)
    if built is None or len(built[0]) < 300:
        return None
    seqs, ys, _ = built
    cut = int(len(seqs) * 0.85)
    Xtr, Xte = seqs[:cut], seqs[cut:]
    Xtr, Xte = _standardize(Xtr, Xte)
    model = _train(kind, Xtr, ys[:cut])
    pred = _predict(model, Xte)
    return metric_fn(ys[cut:], pred, ref)


def predict_latest(kind: str, X: np.ndarray, y_all: np.ndarray) -> float | None:
    built = _build_sequences(X, y_all)
    if built is None:
        return None
    seqs, ys, _ = built
    last_window = X[-L:][None, :, :].astype(np.float32)
    Xtr, last = _standardize(seqs, last_window)
    model = _train(kind, Xtr, ys)
    return float(max(0.0, _predict(model, last)[0]))
