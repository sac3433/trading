const express = require('express');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 3000;

// Middleware
app.use(express.json());

// CORS middleware for local development
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE');
  res.header('Access-Control-Allow-Headers', 'Content-Type');
  next();
});

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Update token endpoint
app.post('/api/update-token', (req, res) => {
  try {
    // Add debugging information
    console.log('Request body:', req.body);
    console.log('Request headers:', req.headers);
    
    const { token } = req.body;
    
    // Add more detailed debugging
    console.log('Extracted token:', token);
    console.log('Token type:', typeof token);
    console.log('Token length:', token ? token.length : 'undefined');

    // Validate token - adjusted minimum length to 6 characters
    if (!token || typeof token !== 'string' || token.length < 6) {
      console.log('Validation failed:');
      console.log('- Token exists:', !!token);
      console.log('- Is string:', typeof token === 'string');
      console.log('- Length >= 6:', token ? token.length >= 6 : false);
      
      return res.status(400).json({ 
        success: false, 
        message: 'Invalid token format - token must be at least 6 characters' 
      });
    }

    // File path in the shared volume
    const tokenFilePath = '/app/config/session_token.txt';
    const configDir = path.dirname(tokenFilePath);

    // Ensure directory exists
    if (!fs.existsSync(configDir)) {
      fs.mkdirSync(configDir, { recursive: true });
    }

    // Write token to file
    fs.writeFileSync(tokenFilePath, token.trim());

    console.log(`[${new Date().toISOString()}] Token successfully written to ${tokenFilePath}`);

    res.json({ 
      success: true, 
      message: 'Token updated successfully! Will take effect on next trading session.' 
    });

  } catch (error) {
    console.error('Error updating token:', error);
    res.status(500).json({ 
      success: false, 
      message: 'Internal server error' 
    });
  }
});

app.listen(PORT, '0.0.0.0', () => {
  console.log(`API server running on port ${PORT}`);
}); 