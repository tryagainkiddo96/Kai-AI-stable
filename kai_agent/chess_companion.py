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

    def best_move(self, board: object) -> Tuple[Optional[object], Optional[str]]:
        # If no board or chess not available, signal unavailable
        if board is None:
            return None, None
        # Try engine if available
        if self.engine and self._has_engine_lib:
            try:
                import chess  # type: ignore
                result = self.engine.play(board, chess.engine.Limit(depth=self.depth))  # type: ignore
                move = result.move  # type: ignore
                san = board.san(move) if move else None  # type: ignore
                return move, san
            except Exception:
                pass
        # Fallback: first legal move
        try:
            moves = list(board.legal_moves)  # type: ignore
        except Exception:
            return None, None
        if not moves:
            return None, None
        move = moves[0]
        san = board.san(move) if hasattr(board, 'san') else str(move)
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
