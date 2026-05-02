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

import chess
import chess.engine


class VisionModule:
    def detect_board(self, source: Optional[str]) -> chess.Board:
        """Return a Board object representing the current position.
        If no source is provided, start from the standard initial position.
        If the source looks like a FEN string, parse it; otherwise fall back to start position.
        """
        if not source:
            return chess.Board()
        s = source.strip()
        # Heuristic: if it looks like a FEN (contains '/' and spaces), parse it
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
        if engine_path:
            try:
                self.engine = chess.engine.SimpleEngine.popen_uci(engine_path)
            except Exception:
                self.engine = None

    def best_move(self, board: chess.Board) -> Tuple[Optional[chess.Move], Optional[str]]:
        if self.engine:
            try:
                result = self.engine.play(board, chess.engine.Limit(depth=self.depth))
                move = result.move
                san = board.san(move) if move else None
                return move, san
            except Exception:
                pass
        # Fallback: pick the first legal move (educational, non-destructive)
        moves = list(board.legal_moves)
        if not moves:
            return None, None
        move = moves[0]
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
