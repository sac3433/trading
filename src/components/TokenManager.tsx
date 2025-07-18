import { useState } from "react";

export function TokenManager() {
  const [token, setToken] = useState("");
  const [isUpdating, setIsUpdating] = useState(false);
  const [message, setMessage] = useState("");
  
  const updateToken = async () => {
    if (!token.trim()) {
      setMessage("Please enter a valid token");
      return;
    }
    
    setIsUpdating(true);
    setMessage("");
    
    try {
      // Call the frontend service API endpoint
      const response = await fetch('/api/update-token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: token.trim() })
      });
      
      if (response.ok) {
        setMessage("Token updated successfully! Will take effect on next trading session.");
        setToken(""); // Clear the input
      } else {
        setMessage("Failed to update token. Please try again.");
      }
    } catch (error) {
      setMessage("Error updating token. Please try again.");
    } finally {
      setIsUpdating(false);
    }
  };

  return (
    <div style={{ 
      padding: '20px', 
      border: '1px solid #ccc', 
      borderRadius: '8px',
      margin: '20px 0',
      backgroundColor: '#f9f9f9'
    }}>
      <h3>🔑 Session Token Manager</h3>
      <p>Update your Breeze API session token without restarting the system.</p>
      
      <div style={{ marginBottom: '10px' }}>
        <input
          type="password"
          placeholder="Enter new session token..."
          value={token}
          onChange={(e) => setToken(e.target.value)}
          style={{ 
            width: '300px', 
            padding: '8px', 
            marginRight: '10px',
            border: '1px solid #ddd',
            borderRadius: '4px'
          }}
        />
        <button 
          onClick={updateToken}
          disabled={isUpdating}
          style={{
            padding: '8px 16px',
            backgroundColor: '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: isUpdating ? 'not-allowed' : 'pointer'
          }}
        >
          {isUpdating ? "Updating..." : "Update Token"}
        </button>
      </div>
      
      {message && (
        <div style={{ 
          padding: '8px', 
          backgroundColor: message.includes('successfully') ? '#d4edda' : '#f8d7da',
          border: `1px solid ${message.includes('successfully') ? '#c3e6cb' : '#f5c6cb'}`,
          borderRadius: '4px',
          color: message.includes('successfully') ? '#155724' : '#721c24'
        }}>
          {message}
        </div>
      )}
      
      <small style={{ color: '#666' }}>
        ℹ️ The new token will be used when the next trading session starts (9:00 AM IST).
      </small>
    </div>
  );
} 