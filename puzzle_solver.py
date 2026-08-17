#!/usr/bin/env python3.12
"""ATF Puzzle Solver — extracts slot position from SVG translate()"""
import re

def solve_puzzle(board_svg: str, piece_svg: str, start_x: float = 10, max_x: float = 258) -> dict:
    """
    Solves ATF withdraw slider puzzle.
    
    Strategy: Find the dashed stroke group in the board SVG which contains
    a path with transform="translate(X Y) scale(S)". The translate X value
    IS the slot's left-edge position on the 320px board, which maps directly
    to the slider offset value.
    
    Args:
        board_svg: Board SVG string from get_withdraw_puzzle response
        piece_svg: Piece SVG string (for validation)
        start_x: Slider start position
        max_x: Slider maximum position
    
    Returns:
        dict with 'offset', 'valid', 'slot_x', 'slot_y', 'confidence'
    """
    # Find the dashed stroke group (the slot outline)
    # Pattern: stroke-dasharray appears inside a <g> with a child <path> that has transform
    dash_idx = board_svg.find('stroke-dasharray')
    if dash_idx == -1:
        return {'offset': None, 'valid': False, 'error': 'No dashed stroke found'}
    
    # Find the path inside this group with transform="translate(X Y)"
    group_content = board_svg[max(0, dash_idx - 200):dash_idx + 500]
    translate_match = re.search(
        r'translate\(([\d.]+)\s+([\d.]+)\)\s+scale\(([\d.]+)\)', 
        group_content
    )
    
    if not translate_match:
        # Fallback: search entire SVG
        translate_match = re.search(
            r'stroke-dasharray[^>]*>.*?translate\(([\d.]+)\s+([\d.]+)\)\s+scale\(([\d.]+)\)',
            board_svg, re.DOTALL
        )
    
    if not translate_match:
        return {'offset': None, 'valid': False, 'error': 'No translate() found in dashed group'}
    
    slot_x = float(translate_match.group(1))
    slot_y = float(translate_match.group(2))
    slot_scale = float(translate_match.group(3))
    
    # The slider offset = slot_x (piece left edge alignment)
    # The piece SVG path starts at M0,0 and extends to H52 (52px wide)
    # The dashed slot path also starts at M0,0 and extends to H52
    # So translate(X) means the slot LEFT EDGE is at board X
    # And slider_offset = piece LEFT EDGE position = slot LEFT EDGE = X
    
    offset = slot_x
    
    # Validate: offset must be within slider range
    if offset < start_x or offset > max_x:
        return {
            'offset': offset, 
            'valid': False, 
            'error': f'Offset {offset} outside slider range [{start_x}, {max_x}]',
            'slot_x': slot_x, 'slot_y': slot_y, 'slot_scale': slot_scale
        }
    
    return {
        'offset': round(offset, 2),
        'valid': True,
        'slot_x': slot_x,
        'slot_y': slot_y, 
        'slot_scale': slot_scale,
        'confidence': 'high'
    }


def build_motion(start_x: float, target: float, duration_ms: int, steps: int = 25) -> list:
    """Build realistic motion array with ease-in-out curve + jitter"""
    import random
    motion = []
    for i in range(steps + 1):
        ratio = i / steps
        ease = ratio * ratio * (3 - 2 * ratio)  # smooth ease-in-out
        x = start_x + (target - start_x) * ease
        t = duration_ms * ratio
        jitter = random.uniform(-0.3, 0.3)
        motion.append({"x": round(x + jitter, 2), "t": round(t, 1)})
    return motion


if __name__ == '__main__':
    # Test with saved SVGs
    with open('/tmp/puzzle_board.svg') as f:
        board = f.read()
    with open('/tmp/puzzle_piece.svg') as f:
        piece = f.read()
    
    result = solve_puzzle(board, piece)
    print(f"Solution: {result}")
