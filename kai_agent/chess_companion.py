"""Educational Chess Companion AI (safety-first)

This module provides a lightweight, safe chess companion that can:
- Detect a board state (via a placeholder vision module)
- Use a chess engine (Stockfish if available) to suggest moves
- Narrate moves in a friendly, conversational tone (no exploits)
This is strictly educational and safe; it does not attempt network access
or exploitation.
"""
from __future__ import annotations

import os
import re
from typing import Optional, Tuple

# note: chess is loaded lazily to support environments without python-chess installed


class VisionModule:
    def detect_board(self, source: Optional[str]) -> object:
        """Return a chess.Board-like object if python-chess is available.
        If python-chess is not installed, return None to indicate unavailability.
        Tries screen OCR for FEN first, then source string, then file path, then default.
        """
        try:
            import chess  # type: ignore
        except Exception:
            return None
        if not source:
            return chess.Board()
        s = source.strip()
        # Heuristic: if it looks like a FEN (contains '/' and digits), parse it
        if "/" in s and any(ch.isdigit() for ch in s):
            try:
                return chess.Board(s)
            except Exception:
                pass
        # If it's a path to a file, attempt to read a line containing FEN
        if os.path.exists(s):
            try:
                with open(s, "r", encoding="utf-8") as f:
                    for line in f:
                        if "/" in line and any(ch.isdigit() for ch in line):
                            return chess.Board(line.strip())
            except Exception:
                pass
        # Fallback to starting position
        return chess.Board()


class EngineWrapper:
    def __init__(self, engine_path: Optional[str] = None, depth: int = 6):
        self.engine = None
        self.depth = depth
        self._has_engine_lib = False
        # Try to lazily import chess and engine libs
        try:
            import chess  # type: ignore
            import chess.engine  # type: ignore
            self._has_engine_lib = True
        except Exception:
            self._has_engine_lib = False
        if engine_path and self._has_engine_lib:
            try:
                self.engine = chess.engine.SimpleEngine.popen_uci(engine_path)  # type: ignore
            except Exception:
                self.engine = None
        # Try common Stockfish locations as fallback
        if not self.engine and self._has_engine_lib:
            import shutil, sys
            for name in ["stockfish", "stockfish.exe", "sf", "sf.exe"]:
                path = shutil.which(name)
                if path:
                    try:
                        self.engine = chess.engine.SimpleEngine.popen_uci(path)
                        break
                    except Exception:
                        self.engine = None

    OPENING_BOOK = {"e4", "d4", "Nf3", "c4", "g3", "b3", "e3", "d3", "Nc3", "f4"}

    def best_move(self, board: object) -> Tuple[Optional[object], Optional[str]]:
        if board is None:
            return None, None

        # Try full UCI engine if available
        if self.engine and self._has_engine_lib:
            try:
                import chess  # type: ignore
                result = self.engine.play(board, chess.engine.Limit(depth=self.depth))
                move = result.move
                san = board.san(move) if move else None
                return move, san
            except Exception:
                pass

        try:
            import chess  # type: ignore
            moves = list(board.legal_moves)
        except Exception:
            return None, None
        if not moves:
            return None, None

        # Heuristic fallback: prefer opening book moves, captures, center control
        scored = []
        for m in moves:
            score = 0
            san = board.san(m)
            # Prefer opening book moves
            if san in self.OPENING_BOOK:
                score += 10
            # Prefer captures
            if board.is_capture(m):
                score += 5
            # Prefer center control (e4, d4, e5, d5)
            to_sq = m.to_square
            if to_sq in (28, 35, 36, 27):  # e4, d4, e5, d5
                score += 3
            # Penalize moving the same piece twice in opening
            if board.fullmove_number <= 5 and board.piece_type_at(m.from_square) == chess.KNIGHT:
                score -= 1
            # Penalize moving king in opening
            if board.fullmove_number <= 10 and board.piece_type_at(m.from_square) == chess.KING:
                score -= 3
            # Prefer developing knights to natural squares
            if san in ("Nf3", "Nc3", "Nf6", "Nc6"):
                score += 2
            scored.append((score, m))

        scored.sort(key=lambda x: -x[0])
        move = scored[0][1]
        san = board.san(move)
        return move, san

    def close(self) -> None:
        if self.engine:
            try:
                self.engine.quit()
            except Exception:
                pass


class ChessCompanion:
    def __init__(self, engine_path: Optional[str] = None):
        self.vision = VisionModule()
        self.engine = EngineWrapper(engine_path=engine_path, depth=6)

    def watch_board(self, source: Optional[str] = None) -> str:
        board = self.vision.detect_board(source)
        move, san = self.engine.best_move(board)
        if move is None:
            return "No legal moves available."
        # Apply the move to show the next position (for narration)
        board_after = board.copy()
        board_after.push(move)
        fen_before = board.fen()
        fen_after = board_after.fen()
        narration = (
            f"Your move: {san}. From the initial position, after {san}, the new FEN is: {fen_after}. "
            f"I can continue with deeper analysis if you want."
        )
        return (
            f"Board FEN before: {fen_before}\n"
            f"Best move: {san} ({move.uci()})\n"
            f"Board FEN after: {fen_after}\n"
            f"Narration: {narration}"
        )
