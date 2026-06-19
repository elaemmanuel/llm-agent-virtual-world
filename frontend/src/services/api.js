// frontend/src/services/api.js
/**
 * API Service
 * 
 * Handles all HTTP communication with the backend FastAPI server.
 * 
 * Backend is running on: http://localhost:8000
 * 
 * This service provides methods for:
 * - Starting tasks
 * - Getting task results
 * - Managing world objects
 * - Retrieving observations
 */

import axios from 'axios';

// ===== CONFIGURATION =====

// Backend URL - change this if your backend runs on a different address
const API_BASE_URL = 'http://localhost:8000';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ===== ERROR HANDLING =====

/**
 * Handle API errors in a user-friendly way
 */
const handleError = (error) => {
  if (error.response) {
    // Server responded with error status
    console.error('API Error:', error.response.status, error.response.data);
    return {
      status: 'error',
      message: error.response.data?.message || `Error: ${error.response.status}`,
      details: error.response.data,
    };
  } else if (error.request) {
    // Request made but no response
    console.error('No response from server');
    return {
      status: 'error',
      message: 'No response from server. Is the backend running?',
      details: error.message,
    };
  } else {
    // Error in request setup
    console.error('Error:', error.message);
    return {
      status: 'error',
      message: error.message,
      details: error,
    };
  }
};

// ===== HEALTH CHECK =====

export const checkHealth = async () => {
  /**
   * Check if backend is running
   * 
   * Returns: { status: 'healthy', app_name: '...', version: '...' }
   */
  try {
    const response = await api.get('/health');
    return response.data;
  } catch (error) {
    return handleError(error);
  }
};

// ===== WORLD MANAGEMENT =====

export const setupWorld = async (objects) => {
  /**
   * Add objects to the world
   * 
   * Args:
   *   objects: Array of object definitions
   *   [
   *     {
   *       id: 1,
   *       name: "Red Cube",
   *       object_type: "cube",
   *       position: [5, 0, 5],
   *       color: "red",
   *       pickupable: true
   *     },
   *     ...
   *   ]
   * 
   * Returns: { status: 'success', objects_added: 3, world_status: {...} }
   */
  try {
    const response = await api.post('/world/setup', objects);
    return response.data;
  } catch (error) {
    return handleError(error);
  }
};

export const getWorldStatus = async () => {
  /**
   * Get current world state
   * 
   * Returns: {
   *   status: 'success',
   *   world: {
   *     agent_position: [x, y, z],
   *     agent_direction: 'north',
   *     agent_inventory: [...],
   *     step_count: 0,
   *     num_objects: 3,
   *     world_size: { x: 20, y: 10, z: 20 }
   *   }
   * }
   */
  try {
    const response = await api.get('/world/status');
    return response.data;
  } catch (error) {
    return handleError(error);
  }
};

export const getObservation = async (task = '') => {
  /**
   * Get what the agent currently perceives
   * 
   * Args:
   *   task: Current task description
   * 
   * Returns: {
   *   status: 'success',
   *   observation: {
   *     agent_state: {...},
   *     visible_objects: [...],
   *     inventory: [...],
   *     environment_context: {...}
   *   }
   * }
   */
  try {
    const response = await api.get('/world/observation', {
      params: { task },
    });
    return response.data;
  } catch (error) {
    return handleError(error);
  }
};

// ===== TASK MANAGEMENT =====

export const startTask = async (taskDescription, maxSteps = 100) => {
  /**
   * Start a new agent task
   * 
   * Args:
   *   taskDescription: What the agent should do
   *   maxSteps: Maximum actions allowed (default 100)
   * 
   * Returns: {
   *   status: 'success',
   *   task_result: {
   *     success: true/false,
   *     status: 'success'|'failed'|'timeout',
   *     steps_taken: 12,
   *     final_position: [x, y, z],
   *     inventory: [...],
   *     session_id: 1,
   *     duration_seconds: 5.23
   *   }
   * }
   * 
   * NOTE: This is a blocking call - it will wait for the task to complete
   * Takes 5-30 seconds depending on task complexity
   */
  try {
    // FIX: Send as query parameters, not JSON body
    const response = await api.post('/tasks/start', null, {
      params: {
        task_description: taskDescription,
        max_steps: maxSteps,
      },
    });
    return response.data;
  } catch (error) {
    return handleError(error);
  }
};

export const getTaskStatus = async (taskId) => {
  /**
   * Get details and results of a completed task
   * 
   * Args:
   *   taskId: Session ID (from startTask response)
   * 
   * Returns: {
   *   status: 'success',
   *   task: {
   *     id: 1,
   *     task_description: '...',
   *     agent_name: 'claude-opus-4-6',
   *     status: 'success',
   *     success: true,
   *     steps_taken: 12,
   *     max_steps: 100,
   *     created_at: '2026-05-20T...',
   *     completion_time: '2026-05-20T...'
   *   }
   * }
   */
  try {
    const response = await api.get(`/tasks/${taskId}`);
    return response.data;
  } catch (error) {
    return handleError(error);
  }
};

export const getTaskActions = async (taskId) => {
  /**
   * Get all actions (steps) taken during a task
   * 
   * Args:
   *   taskId: Session ID
   * 
   * Returns: {
   *   status: 'success',
   *   task_id: 1,
   *   action_count: 12,
   *   actions: [
   *     {
   *       step_number: 1,
   *       action_type: 'move',
   *       action_args: { direction: 'forward' },
   *       success: true,
   *       result_message: '...',
   *       position_before: [x, y, z],
   *       position_after: [x, y, z],
   *       created_at: '...'
   *     },
   *     ...
   *   ]
   * }
   */
  try {
    const response = await api.get(`/tasks/${taskId}/actions`);
    return response.data;
  } catch (error) {
    return handleError(error);
  }
};

// ===== WEBSOCKET MANAGEMENT =====

/**
 * Connect to WebSocket for real-time task updates
 * 
 * Args:
 *   taskId: Session ID
 *   onMessage: Callback function when message received
 *   onError: Callback function on error
 *   onClose: Callback function when connection closes
 * 
 * Returns: WebSocket instance
 * 
 * Usage:
 *   const ws = connectWebSocket(1, 
 *     (data) => console.log('Update:', data),
 *     (error) => console.error('Error:', error),
 *     () => console.log('Connection closed')
 *   );
 *   
 *   // Later, close the connection:
 *   ws.close();
 */
export const connectWebSocket = (taskId, onMessage, onError, onClose) => {
  try {
    // Construct WebSocket URL
    const wsUrl = `ws://localhost:8000/ws/${taskId}`;
    console.log('Connecting to WebSocket:', wsUrl);
    
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      console.log('WebSocket connected');
    };
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        console.log('WebSocket message:', data);
        onMessage(data);
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };
    
    ws.onerror = (event) => {
      console.error('WebSocket error:', event);
      if (onError) onError(event);
    };
    
    ws.onclose = () => {
      console.log('WebSocket disconnected');
      if (onClose) onClose();
    };
    
    return ws;
  } catch (error) {
    console.error('Error connecting to WebSocket:', error);
    return null;
  }
};

// ===== EXPORT ALL =====

export default {
  checkHealth,
  setupWorld,
  getWorldStatus,
  getObservation,
  startTask,
  getTaskStatus,
  getTaskActions,
  connectWebSocket,
};