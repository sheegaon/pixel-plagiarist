# 🚀 Deploying Pixel Plagiarist to Heroku

This guide will walk you through deploying your Pixel Plagiarist multiplayer drawing game to Heroku for online play.

## 📋 Prerequisites

Before starting, make sure you have:

1. **Heroku Account**: Sign up at [heroku.com](https://www.heroku.com) (free tier available)
2. **Git**: Installed on your system
3. **Heroku CLI**: Download from [devcenter.heroku.com/articles/heroku-cli](https://devcenter.heroku.com/articles/heroku-cli)
4. **Working Game**: Your Pixel Plagiarist game should run locally first

## 🛠️ Step 1: Prepare Your Application

### 1.1 Generate Secure Secret Key

Run the key generator:
```bash
python generate_secret_key.py
```

Copy the generated key for use in Step 3.

## 🚀 Step 2: Deploy to Heroku

### 2.1 Login to Heroku
```bash
heroku login
```

### 2.2 Create Heroku App
```bash
heroku create pixel-plagiarist
```

### 2.3 Set Environment Variables
```bash
# Set the secure secret key (use the one from generate_secret_key.py)
heroku config:set SECRET_KEY="your-64-character-secret-key-here"

# Optional: Set other config vars
heroku config:set FLASK_ENV=production
```

### 2.4 Deploy Your Code
```bash
git add .
git commit -m "Deploy Pixel Plagiarist to Heroku"
git push heroku main
```

### 2.5 Scale Your App
```bash
heroku ps:scale web=1
```

## 🌐 Step 3: Access Your Game

Your game will be available at:
```
https://pixel-plagiarist.herokuapp.com
```

## 🔍 Step 4: Monitor and Debug

### View Logs
```bash
heroku logs --tail
```

### Check App Status
```bash
heroku ps
```

### Open in Browser
```bash
heroku open
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Example           |
|----------|-------------|-------------------|
| `SECRET_KEY` | **Required** - Flask session security | `a1b2c3d4e5f6...` |
| `TESTING_MODE` | Enable testing mode (5-second timers) | `true` / `false`  |
| `COUNTDOWN_TIMER` | Seconds to wait for more players | `20` (default)    |
| `BETTING_TIMER` | Seconds for betting phase | `10` (default)    |
| `DRAWING_TIMER` | Seconds for drawing phase | `60` (default)    |
| `COPYING_TIMER` | Seconds for copying phase | `60` (default)    |
| `VOTING_TIMER` | Seconds per voting round | `30` (default)    |
| `PORT` | Heroku sets automatically | `5000`            |
| `FLASK_ENV` | Flask environment | `production`      |

### Testing Mode

Enable testing mode for rapid gameplay testing and development:

```bash
# Enable testing mode (all timers become 5 seconds)
heroku config:set TESTING_MODE=true

# Disable testing mode (use normal/custom timers)
heroku config:set TESTING_MODE=false
```

**What Testing Mode Does:**
- **Countdown Timer**: 5 seconds (instead of 20) to wait for more players
- **Betting Phase**: 5 seconds (instead of 10) for placing bets
- **Drawing Phase**: 5 seconds (instead of 60) for creating original drawings
- **Copying Phase**: 5 seconds (instead of 60) for copying other drawings
- **Voting Rounds**: 5 seconds (instead of 10) per voting set

**When to Use Testing Mode:**
- ✅ Development and debugging
- ✅ Quick functionality testing
- ✅ Demonstrating game flow rapidly
- ❌ **Not recommended for actual gameplay** (too fast for players)

### Custom Timer Configuration

For fine-tuned control without testing mode, set individual timers:

```bash
# Custom timer examples
heroku config:set COUNTDOWN_TIMER=30    # 30 seconds for player countdown
heroku config:set DRAWING_TIMER=90     # 90 seconds for drawing phase  
heroku config:set COPYING_TIMER=45     # 45 seconds for copying phase
heroku config:set VOTING_TIMER=15      # 15 seconds per voting round
```

**Timer Hierarchy:**
1. If `TESTING_MODE=true`: All timers = 5 seconds (overrides everything)
2. If individual timer variables are set: Use those values
3. Otherwise: Use built-in defaults (20, 10, 60, 60, 10 seconds)

View current config:
```bash
heroku config
```

Set new variables:
```bash
heroku config:set VARIABLE_NAME="value"
```

## 🚨 Troubleshooting

### Common Issues

1. **App won't start**:
   ```bash
   heroku logs --tail
   ```
   Check for Python errors or missing dependencies.

2. **Port binding errors**:
   Ensure your server.py uses `os.environ.get('PORT', 5000)`

3. **Static files not loading**:
   Heroku serves static files automatically for Flask apps.

4. **WebSocket connection issues**:
   Heroku supports WebSockets by default, but check CORS settings.

### Performance Tips

1. **Enable gzip compression** (add to server.py):
   ```python
   from flask_compress import Compress
   Compress(app)
   ```

2. **Use CDN for assets**: Consider using a CDN for the Socket.IO library

3. **Monitor response times**: Use Heroku metrics or add logging

### Scaling

For more concurrent players:
```bash
# Scale to 2 dynos
heroku ps:scale web=2

# Check dyno usage
heroku ps
```

## 🔐 Security Considerations

### For Production Use

1. **Change Secret Key**:
   ```bash
   heroku config:set SECRET_KEY="your-super-secret-key-here"
   ```

   Update server.py:
   ```python
   app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'pixel_plagiarist_secret_key')
   ```

2. **Rate Limiting**: Consider adding rate limiting for drawing submissions

3. **Input Validation**: Add validation for room codes, usernames, etc.

## 🎯 Testing Your Deployment

### Multi-Device Testing

1. **Desktop**: Open your Heroku URL in multiple browser tabs
2. **Mobile**: Test on phones/tablets using the same URL
3. **Network**: Test from different WiFi networks to simulate real users

### Load Testing

For high-traffic scenarios:
```bash
# Install artillery for load testing
npm install -g artillery

# Create test script to simulate multiple players
```

## 🔄 Updates and Maintenance

### Deploy Updates
```bash
git add .
git commit -m "Update game features"
git push heroku main
```

### Backup Important Data
```bash
# If you add database features later
heroku pg:backups:capture
```

### Monitor Resource Usage
```bash
heroku ps
heroku logs --tail
```

## 🆘 Support

- [Heroku Documentation](https://devcenter.heroku.com/)
- [Flask-SocketIO Documentation](https://flask-socketio.readthedocs.io/)
- [Heroku Support](https://help.heroku.com/)
