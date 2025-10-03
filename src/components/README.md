# Terminal Window Component

A Vue component that creates a macOS-style terminal window in dark mode. It can be minimized, opened, and dragged around the screen.

## Features

- **macOS Terminal Style**: Dark mode with the classic macOS terminal appearance
- **Minimizable**: Click the yellow button to minimize to a small icon on the left side
- **Draggable**: Click and drag the terminal header to move it around
- **Command Input**: Uses the TerminalInput component for command entry
- **Command History**: Displays previous commands and outputs
- **Theming**: Supports both light and dark themes
- **Customizable**: Easily change the title and initial output

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `title` | String | 'Terminal' | The title displayed in the terminal header |
| `initialOutput` | Array | ['Welcome to Terminal'] | Initial lines displayed in the terminal |
| `theme` | String | 'dark' | Theme of the terminal ('dark' or 'light') |

## Events

| Event | Description |
|-------|-------------|
| `close` | Emitted when the close button is clicked |
| `submit` | Emitted when a command is submitted (inherited from TerminalInput) |
| `update:theme` | Emitted when the theme is changed (for v-model binding) |

## Usage

### Basic Usage

```vue
<template>
  <TerminalWindow
    title="nickberens ~ bash"
    :initialOutput="['Welcome to Terminal', 'Type help for available commands']"
    @close="handleClose"
  />
</template>

<script>
import TerminalWindow from './components/TerminalWindow.vue';

export default {
  components: {
    TerminalWindow
  },
  methods: {
    handleClose() {
      // Handle close event
      console.log('Terminal closed');
    }
  }
}
</script>
```

### With Theme Control (Two-way binding)

```vue
<template>
  <div>
    <button @click="toggleTheme">Toggle Theme</button>

    <TerminalWindow
      v-model:theme="currentTheme"
      title="Terminal"
      :initialOutput="['Type \'theme\' to toggle between light and dark mode']"
    />

    <div class="theme-status">
      Current theme: {{ currentTheme }}
    </div>
  </div>
</template>

<script>
import { ref } from 'vue';
import TerminalWindow from './components/TerminalWindow.vue';

export default {
  components: {
    TerminalWindow
  },
  setup() {
    const currentTheme = ref('dark');

    const toggleTheme = () => {
      currentTheme.value = currentTheme.value === 'dark' ? 'light' : 'dark';
    };

    return {
      currentTheme,
      toggleTheme
    };
  }
}
</script>
```

With this setup:
1. The theme can be changed by clicking the button (parent component control)
2. The theme can also be changed by typing the 'theme' command in the terminal
3. The current theme is displayed and stays in sync between both methods

## Built-in Commands

The terminal component comes with several built-in commands:

| Command | Description |
|---------|-------------|
| `clear` | Clears the terminal output |
| `help` | Displays a list of available commands |
| `theme` | Toggles between light and dark themes |
| `version` | Displays the terminal version information |

## Extending Command Handling

You can extend or modify the command handling by editing the `handleCommand` method in the component. Here's the current implementation:

```javascript
// Inside the TerminalWindow.vue component
const handleCommand = (command) => {
  outputLines.value.push(`${command}`);

  // Process commands
  if (command === 'clear') {
    outputLines.value = [];
  } else if (command === 'help') {
    outputLines.value.push('Available commands:');
    outputLines.value.push('- clear: Clear the terminal');
    outputLines.value.push('- help: Show this help message');
    outputLines.value.push('- theme: Toggle between light and dark theme');
    outputLines.value.push('- version: Show terminal version');
  } else if (command === 'theme') {
    // Toggle theme
    const newTheme = props.theme === 'dark' ? 'light' : 'dark';
    emit('update:theme', newTheme);
    outputLines.value.push(`Theme switched to ${newTheme} mode`);
  } else if (command === 'version') {
    outputLines.value.push('Terminal v1.0.0');
    outputLines.value.push('Created by nickberens');
  } else {
    outputLines.value.push(`Command not found: ${command}`);
  }

  // Clear the input and scroll to bottom
  // ...
};
```

## Example Component

See the `TerminalWindowExample.vue` in the examples directory for a complete working example of how to use the TerminalWindow component with theme switching and visibility controls.
