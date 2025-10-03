/**
 * Single source of truth for all terminal default values.
 */

export const DEFAULT_TERMINAL = {
  position: {
    x: 20,
    y: 100,
  },
  size: {
    width: 315,
    height: 290,
  },
  margin: 20,
  helpOutput: [
    'Available commands:',
    '- clear: Clear the terminal',
    '- bust-cache: Clear localStorage (with confirmation)',
    '- help: Show this help message',
    '- theme: Toggle between light and dark theme',
    '- version: Show terminal version',
    '- ls: List navigation links',
    '- cd [nav item name]: Navigate to a nav item',
    '- cd / or cd home: Navigate to the index page',
    '- git log: Show commit history',
    '- git graph: Show code frequency chart',
  ],
  output: [
    'Type "help" for a list of commands.',
  ],
}

// Settings for maximized terminal window
export const MAXIMIZED_TERMINAL = {
  margin: 0, // 20px from all edges of the screen
}
