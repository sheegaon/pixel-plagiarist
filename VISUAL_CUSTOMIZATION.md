# Pixel Plagiarist Visual Customization Guide

## Overview
The game includes an asset management system that provides attractive default styling and allows easy replacement of individual visual elements with custom graphics. The system gracefully falls back to default styling when custom images aren't available.

## Directory Structure
```
static/
├── images/
│   ├── game-logo.png                 # Main game logo (replaces emoji in title)
│   ├── game-background.jpg           # Main background image
│   ├── icons/
│   │   ├── exit-icon.png            # Exit/leave room button
│   │   ├── paint-icon.png           # Drawing/art related icons  
│   │   ├── trophy-icon.png          # Leaderboard/trophy icon
│   │   ├── refresh-icon.png         # Refresh button
│   │   ├── timer-icon.png           # Timer related icons
│   │   ├── users-icon.png           # Player/user icons
│   │   └── coins-icon.png           # Money/balance icons
│   ├── ui/
│   │   ├── timer-bg.png             # Timer background decoration
│   │   ├── canvas-border.png        # Drawing canvas border image
│   │   └── button-bg.png            # Custom button backgrounds
│   └── themes/
│       └── [theme folders for future expansion]
```

## Default Styling

### Visual Design Elements
- **Animated gradient background** with smooth color transitions
- **Glass-morphism UI elements** with blur effects and transparency
- **Styled buttons** with gradients, shadows, and hover animations
- **Pulsing timer** with red gradient styling
- **Modern typography** with gradient text effects
- **Smooth transitions** and micro-animations throughout

### Custom Image Integration
When images are added to the appropriate folders, they automatically replace the default elements:

## Customization Steps

### 1. Replace Background
- Add `game-background.jpg` to `/static/images/`
- Supports: JPG, PNG, WebP formats
- Recommended: High resolution, landscape orientation
- The animated gradient remains as fallback

### 2. Add Custom Logo
- Add `game-logo.png` to `/static/images/`
- Recommended size: 48px height (width auto-scales)
- Appears next to the game title
- Title text remains for branding

### 3. Replace Icons
Add any of these to `/static/images/icons/`:
- `exit-icon.png` - Leave room button
- `trophy-icon.png` - Leaderboard button  
- `refresh-icon.png` - Refresh rooms button
- `paint-icon.png` - Art/drawing related elements
- `timer-icon.png` - Timer decorations
- `users-icon.png` - Player count displays
- `coins-icon.png` - Balance/money displays

Icons automatically replace emojis when available, with smooth transitions.

### 4. UI Element Customization
Add to `/static/images/ui/`:
- `timer-bg.png` - Background decoration for countdown timers
- `canvas-border.png` - Custom border around drawing canvases
- `button-bg.png` - Background texture for themed buttons

## Development Console Commands

For testing and development, assets can be replaced at runtime:

```javascript
// Replace an icon
assetManager.replaceAsset('icons', 'exit', '../images/icons/custom-exit.png');

// Replace background
assetManager.replaceAsset('backgrounds', 'main', '../images/new-background.jpg');

// Check current assets
console.log(assetManager.assets);
```

## Image Specifications

### Backgrounds
- **Main background**: 1920x1080+ recommended for full coverage
- **UI backgrounds**: 200x100+ depending on element size
- **Formats**: JPG (smaller file size), PNG (transparency support), WebP (modern browsers)

### Icons
- **Size**: 20x20px to 64x64px (auto-scaling applied)
- **Format**: PNG recommended for transparency support
- **Style**: Should work on both light and dark backgrounds

### Logos
- **Height**: 48px recommended (width scales proportionally)
- **Format**: PNG for transparency, SVG for crisp scaling
- **Style**: Should complement the gradient title text

## Current Visual Theme

### Color Palette
- **Primary**: Blue gradients (#4299e1 to #3182ce)
- **Success**: Green gradients (#48bb78 to #38a169)  
- **Warning/Timer**: Red gradients (#e53e3e variants)
- **Background**: Purple-pink gradient animation

### Visual Effects
- **Glass morphism**: Translucent panels with backdrop blur
- **Smooth animations**: 0.3s transitions on hover/interaction
- **Gradient borders**: Canvas and UI elements feature gradient borders
- **Pulsing timer**: Subtle scale animation for urgency indication
- **Hover effects**: Lift and glow effects on interactive elements

## Implementation Approach

1. **Start with background**: Add a custom `game-background.jpg` for immediate visual impact
2. **Add branding**: Create a `game-logo.png` for brand recognition
3. **Replace icons incrementally**: Add icons one by one as they're created
4. **Customize specific elements**: Use the UI folder for detailed customizations

The system is designed to allow incremental visual customization without breaking functionality. Each addition enhances the game's visual uniqueness while maintaining the polished default appearance for uncustomized elements.