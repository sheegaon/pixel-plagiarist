# Pixel Plagiarist Visual Customization Guide

## Overview
Your game has a simple asset management system that looks great by default and makes it easy to replace individual visual elements as you create custom graphics. The system gracefully falls back to the default styling when custom images aren't available.

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
│       └── [future theme folders]
```

## What Gets Applied Automatically

### Default Styling (No Custom Images Needed)
- **Animated gradient background** with smooth color transitions
- **Glass-morphism UI elements** with blur effects and transparency
- **Styled buttons** with gradients, shadows, and hover animations
- **Pulsing timer** with red gradient styling
- **Modern typography** with gradient text effects
- **Smooth transitions** and micro-animations throughout

### Custom Image Integration
When you add images to the appropriate folders, they automatically replace the default elements:

## Easy Customization Steps

### 1. Replace Background
- Add `game-background.jpg` to `/static/images/`
- Supports: JPG, PNG, WebP
- Recommended: High resolution, landscape orientation
- The animated gradient remains as fallback

### 2. Add Custom Logo
- Add `game-logo.png` to `/static/images/`
- Recommended size: 48px height (width auto-scales)
- Appears next to the game title
- Title text remains for branding

### 3. Replace Icons One by One
Add any of these to `/static/images/icons/`:
- `exit-icon.png` - Leave room button
- `trophy-icon.png` - Leaderboard button  
- `refresh-icon.png` - Refresh rooms button
- `paint-icon.png` - Art/drawing related elements
- `timer-icon.png` - Timer decorations
- `users-icon.png` - Player count displays
- `coins-icon.png` - Balance/money displays

Icons automatically replace emojis when available, with smooth transitions.

### 4. Advanced UI Customization
Add to `/static/images/ui/`:
- `timer-bg.png` - Background decoration for countdown timers
- `canvas-border.png` - Custom border around drawing canvases
- `button-bg.png` - Background texture for themed buttons

## Development Console Commands

For testing and development, you can replace assets at runtime:

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
- **Main background**: 1920x1080+ recommended
- **UI backgrounds**: 200x100+ depending on element
- Formats: JPG (smaller file), PNG (transparency), WebP

### Icons
- **Size**: 20x20px to 64x64px (they scale automatically)
- **Format**: PNG recommended for transparency
- **Style**: Should work on both light and dark backgrounds

### Logos
- **Height**: 48px recommended (width auto-scales)
- **Format**: PNG for transparency, SVG for crisp scaling
- **Style**: Should complement the gradient title text

## Current Visual Design

### Color Scheme
- **Primary**: Blue gradients (#4299e1 to #3182ce)
- **Success**: Green gradients (#48bb78 to #38a169)  
- **Warning/Timer**: Red gradients (#e53e3e variants)
- **Background**: Purple-pink gradient animation

### Effects
- **Glass morphism**: Translucent panels with blur
- **Smooth animations**: 0.3s transitions on hover/interaction
- **Gradient borders**: Canvas and elements have gradient borders
- **Pulsing timer**: Subtle scale animation for urgency
- **Hover effects**: Lift and glow on interactive elements

## Next Steps

1. **Start with background**: Add a custom `game-background.jpg` for immediate impact
2. **Add logo**: Create a `game-logo.png` for brand recognition
3. **Replace icons gradually**: Add icons one by one as you create them
4. **Customize specific elements**: Use the UI folder for advanced customizations

The system is designed to let you customize the game's appearance incrementally without breaking anything. Each addition makes the game more visually unique while maintaining the polished default appearance.