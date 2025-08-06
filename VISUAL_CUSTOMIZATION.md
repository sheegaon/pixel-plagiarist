# Pixel Plagiarist Visual Customization Guide

## Overview

Pixel Plagiarist features a flexible asset management system designed to make visual customization straightforward and non-disruptive. The system provides a set of attractive default styles—drawing from modern UI trends like gradients, glass-morphism, and subtle animations—while allowing developers, designers, or users to replace individual elements with custom graphics. If a custom asset isn't provided or fails to load, the game gracefully falls back to its default styling, ensuring the application remains functional and visually coherent.

This guide covers the asset directory structure, default visuals, step-by-step customization processes, technical specifications, best practices, and advanced techniques. Whether you're rebranding the game for a specific audience, integrating thematic elements (e.g., holiday specials), or enhancing accessibility, this system supports incremental changes without requiring code modifications.

The asset manager (implemented in `static/js/asset-manager.js`) scans for files in predefined directories on load and dynamically applies them to UI components. This modular approach minimizes conflicts and supports hot-reloading during development.

## Directory Structure

Assets are organized in a logical hierarchy under the `static/` folder. This structure separates core game images from icons, UI elements, and themes, making it easy to manage and expand.

```
static/
├── images/
│   ├── game-logo.png                 # Main game logo (replaces default title emoji or text)
│   ├── game-background.jpg           # Primary background image (overrides animated gradient)
│   ├── icons/
│   │   ├── exit-icon.png             # Exit/leave room button icon
│   │   ├── paint-icon.png            # Drawing or art-related icons (e.g., brush tool)
│   │   ├── trophy-icon.png           # Leaderboard or achievement icons
│   │   ├── refresh-icon.png          # Refresh button icon
│   │   ├── timer-icon.png            # Timer or countdown icons
│   │   ├── users-icon.png            # Player list or user-related icons
│   │   ├── coins-icon.png            # Balance or token icons
│   │   └── custom-icon-example.png   # Add custom icons as needed (e.g., for new features)
│   ├── ui/
│   │   ├── timer-bg.png              # Background for countdown timers
│   │   ├── canvas-border.png         # Border frame around drawing canvases
│   │   ├── button-bg.png             # Background texture or pattern for buttons
│   │   └── modal-bg.png              # Background for modals and overlays (new in expanded guide)
│   └── themes/
│       ├── default/                  # (Optional) Backup of default assets
│       ├── holiday/                  # Example theme folder (e.g., for seasonal events)
│       │   ├── game-background.jpg   # Theme-specific overrides
│       │   └── icons/                # Subfolder for theme icons
│       └── dark-mode/                # Another example for alternative themes
```

- **Note**: File names are case-sensitive and must match exactly (e.g., `game-logo.png`). Supported formats include PNG (for transparency), JPG (for photos), SVG (for scalable vectors), and WebP (for optimized web delivery). The system prioritizes SVG for icons where possible for better scaling.

## Default Styling

The game's out-of-the-box visuals create an engaging, modern atmosphere inspired by digital art tools and social games. Key elements include:

### Visual Design Elements
- **Animated Gradient Background**: A shifting linear gradient (from #667eea to #f093fb) that animates over 15 seconds, providing a dynamic yet non-distracting canvas.
- **Glass-Morphism UI Elements**: Semi-transparent panels with backdrop blur (e.g., `backdrop-filter: blur(10px)`), subtle borders, and shadows for a premium, layered feel.
- **Styled Buttons**: Gradient backgrounds (#4299e1 to #3182ce), hover animations (scale and shadow lift), and active states for tactile feedback.
- **Pulsing Timer**: Red-toned (#e53e3e) with a subtle glow animation to convey urgency without overwhelming the player.
- **Modern Typography**: Sans-serif fonts (Segoe UI fallback) with gradient text effects on titles and bold weights for readability.
- **Smooth Transitions**: 0.3s ease-in-out animations on hovers, phase changes, and modals for a polished user experience.
- **Canvas Styling**: White backgrounds with gradient borders and pixelated rendering on high-DPI screens for a retro-digital art vibe.

These defaults ensure the game looks professional even without customizations, but they can be overridden progressively.

## Custom Image Integration

When you add files to the directories above, the asset manager automatically detects and integrates them:
- **Replacement Logic**: On page load, the manager checks for custom files and swaps them in (e.g., via CSS `background-image` or JS `img.src`).
- **Fallback Mechanism**: If a custom asset is missing or invalid (e.g., broken link), it reverts to defaults like emojis for icons or pure CSS gradients for backgrounds.
- **Dynamic Updates**: Supports runtime changes via console commands (see below), useful for live previews.

This integration is seamless—no code changes needed for basic swaps.

## Customization Steps

Follow these steps to customize incrementally, starting with high-impact elements.

### 1. Replace the Background
- **File**: Add `game-background.jpg` (or .png/.webp) to `/static/images/`.
- **Effect**: Overrides the animated gradient, applied to the body via CSS.
- **Best Practices**: Use high-contrast images for readability. Compress files (e.g., via TinyPNG) to under 500KB for fast loading.
- **Example**: A starry night sky for a "cosmic art" theme—ensures text and UI elements remain visible.

### 2. Add a Custom Logo
- **File**: Add `game-logo.png` (or .svg) to `/static/images/`.
- **Effect**: Appears beside the game title in headers, replacing any default emoji or text placeholder.
- **Best Practices**: Design for 48px height; include transparency for seamless integration. Use SVG for crisp edges on all devices.
- **Example**: A pixelated artist palette icon to reinforce the drawing theme.

### 3. Replace Icons
- **Files**: Add to `/static/images/icons/` (e.g., `exit-icon.png`).
- **Effect**: Replaces emojis or default SVGs in buttons and UI (e.g., exit icon on leave buttons).
- **Best Practices**: Aim for monochromatic designs that work on light/dark backgrounds. Size: 24-48px square.
- **Example**: A custom trophy icon with game-specific flair, like a plagiarized Mona Lisa.

### 4. Customize UI Elements
- **Files**: Add to `/static/images/ui/` (e.g., `timer-bg.png` for timer backgrounds).
- **Effect**: Enhances specific components, like adding a patterned border to canvases.
- **Best Practices**: Ensure transparency where needed (e.g., PNG for borders). Test on mobile for scaling.
- **New Addition**: Introduce `modal-bg.png` for custom modal backgrounds, applied via CSS.

### 5. Create and Apply Themes (Advanced)
- **Folder**: Add subfolders under `/static/images/themes/` (e.g., `holiday/`).
- **Effect**: Load entire themes via a query parameter (e.g., `?theme=holiday`) or JS config.
- **Best Practices**: Duplicate and modify defaults. Use for events (e.g., Halloween with orange gradients).
- **Example**: A "dark-mode" theme with inverted colors for low-light play.

## Development Console Commands

For testing customizations without restarts:
```javascript
// Replace a specific icon
assetManager.replaceAsset('icons', 'exit', '/static/images/icons/custom-exit.png');

// Swap the main background
assetManager.replaceAsset('backgrounds', 'main', '/static/images/new-background.jpg');

// Load a full theme
assetManager.loadTheme('holiday');

// List current assets for debugging
console.log(assetManager.assets);

// Revert to defaults
assetManager.resetToDefaults();
```

These commands trigger immediate UI updates, ideal for iterative design.

## Image Specifications and Best Practices

### General Guidelines
- **Tools**: Use free tools like Canva, GIMP, or Adobe Photoshop. For vectors: Inkscape or Figma.
- **Optimization**: Compress images (aim <100KB per file) using tools like ImageOptim. Support WebP for modern browsers.
- **Accessibility**: Ensure high contrast (WCAG AA compliant, e.g., 4.5:1 ratio). Add alt text in HTML where applicable.
- **Testing**: Preview on multiple devices (desktop, mobile) and browsers. Use Lighthouse for performance audits.

### Specific Specs
- **Backgrounds**: 1920x1080px minimum; landscape; JPG/WebP; subtle patterns to avoid clashing with UI.
- **Icons**: 24-64px square; PNG/SVG; transparent backgrounds; simple, scalable designs.
- **Logos**: 48px height (auto width); PNG/SVG; bold, recognizable at small sizes.
- **UI Elements**: Vary by component (e.g., timer-bg: 200x100px); PNG for overlays; match game's rounded aesthetics.

## Current Visual Theme and Expansion Ideas

### Color Palette (Defaults)
- Primary: Blues (#4299e1 → #3182ce) for buttons and accents.
- Success: Greens (#48bb78 → #38a169) for positives like votes.
- Warning: Reds (#e53e3e) for timers and errors.
- Background: Purple-pink gradients for energy.

### Visual Effects (Defaults)
- Glass-morphism for depth.
- Animations for engagement (e.g., pulse on timers).
- Hover lifts for interactivity.

### Expansion Ideas
- **Seasonal Themes**: Auto-switch based on date (e.g., Christmas snowflakes).
- **User-Selectable Skins**: Allow players to choose themes via settings.
- **CSS Overrides**: For deeper changes, edit `main.css` (e.g., `--primary-color: #your-hex;` for variables).
- **Accessibility Mode**: Add a high-contrast theme in `/themes/accessibility/` with larger icons and bolder colors.

## Troubleshooting

- **Asset Not Loading**: Check file paths, names, and browser console for 404 errors. Clear cache.
- **Performance Issues**: Oversized images? Compress them. Test with slow connections.
- **Fallback Failures**: Ensure defaults are intact in code. Log issues via `console.error(assetManager.errors)`.
- **Compatibility**: SVG icons may need polyfills for older browsers; test on IE/Edge if needed.

This expanded guide empowers you to transform Pixel Plagiarist's visuals while preserving its core appeal. For code-level integrations or custom scripts, refer to the architecture docs or consult the asset manager module. If you encounter issues, share feedback in the project's issues tracker!