# Dorothy's Mind Games

> *"In this world, moves decide everything."*

A narrative-driven chess roguelike where a young genius named Dorothy is trapped in a metaphysical realm governed by the laws of chess. Every move carries existential weight — brilliant play ascends toward **Heaven**, while blunders fracture reality and plunge you into **Limbo**, a nightmarish puzzle dimension.

---

## Features

- **Full Chess Engine Integration** — Stockfish 16 runs in a background thread, providing real-time position analysis, move classification, and adaptive AI opponents
- **"Genius Vision" System** — Toggle engine overlays (evaluation bar, best-move arrows, threat heat maps) at the cost of Focus resources
- **Blunder → Limbo Mechanic** — Moves losing ≥200 centipawns trigger a transition to a monochromatic puzzle dimension where you must solve tactical puzzles under time pressure to escape
- **Resource Management** — Balance three intertwined resources:
  - **Sanity** — Controls UI reliability. Low sanity causes visual glitches, false evaluations, and distortion
  - **Soul** — Your life force and currency for "Temporal Rewind" (undo moves)
  - **Focus** — Powers Genius Vision. Regenerates each turn; drains when using engine analysis
- **Flow State** — Three consecutive best moves triggers enhanced visuals, fast Focus regeneration, and a heavenly glow
- **Opponent Personas** — Five distinct AI personalities (The Berserker, The Gatekeeper, The Shadow Self, The Prodigy, The Endgame Master), each with unique UCI configurations and narrative taunts
- **Visual Novel Dialogue** — Typewriter-style narrative overlays for story beats and opponent interactions
- **Atmospheric VFX** — Screen shake, noir filters, chromatic aberration, particle effects, vignette, and sanity distortion

## Requirements

- Python 3.11+
- [Stockfish](https://stockfishchess.org/download/) (place `stockfish.exe` on your PATH, or set the path in `src/core/constants.py`)

## Installation

```bash
# Clone the repository
git clone <repo-url>
cd dorothy-s-MindGames

# Install dependencies
pip install -r requirements.txt

# Run the game
python main.py
```

## Controls

| Key | Action |
|-----|--------|
| **Left Click** | Select / move pieces |
| **Right Click (hold)** | Genius Vision — preview engine's principal variation |
| **G** | Toggle Genius Vision overlay (costs Focus) |
| **T** | Toggle Threat Map |
| **R** | Temporal Rewind — undo last move pair (costs Soul) |
| **F** | Flip board |
| **ESC** | Return to menu |
| **↑ / ↓** | Navigate menu |
| **Enter / Space** | Confirm selection / advance dialogue |

## Project Structure

```
main.py                         # Entry point (1280×720, 60 FPS)
src/
  core/
    constants.py               # All configuration values
    state_manager.py           # Stack-based state machine
    resource_manager.py        # Sanity / Soul / Focus systems
  engine/
    analyzer.py                # Async Stockfish integration (threading + UCI)
    opponent.py                # AI persona configurations
  states/
    main_menu_state.py         # Atmospheric menu with persona selection
    game_state.py              # Core chess gameplay loop
    limbo_state.py             # Blunder punishment puzzle dimension
    game_over_state.py         # Heaven / Hell / Void result screen
  ui/
    renderer.py                # 8-layer board renderer + HUD
    dialogue.py                # Visual-novel typewriter dialogue
  vfx/
    particles.py               # Burst + sparkle particle effects
    screen_effects.py          # Shake, vignette, flash effects
assets/
  sprites/                     # Piece images (unicode fallback built-in)
  audio/                       # SFX and ambient tracks
  fonts/                       # Custom fonts
  puzzles/                     # Puzzle FEN files
```

## The Cosmology

| State | Description | Trigger |
|-------|-------------|---------|
| **The Board** | Standard chess reality. Clean, logical, turn-based. | Default |
| **Heaven** | Perfect Information. The solved state. | Checkmate with high accuracy |
| **Limbo** | Noir puzzle dimension. Time pressure. | Blunder (≥200cp loss) |
| **Hell** | Game Over. Absolute chaos. | Soul reaches 0 / Limbo failure |

## Development

This project uses **Cursor AI** as a development accelerator. See `.cursorrules` for the AI engineering framework. The codebase is designed for a single developer or small team to iterate rapidly using AI-assisted code generation.

## License

MIT
