// frontend/src/App.jsx
/**
 * Main App Component
 * 
 * This is the root component that orchestrates:
 * - Layout (header, main content, sidebar)
 * - Navigation between views
 * - Calling backend APIs
 * - Managing global state
 */

import React, { useState, useEffect } from 'react';
import './App.css';
import Viewport3D from './components/Viewport3D';
import ControlPanel from './components/ControlPanel';
import Dashboard from './components/Dashboard';
import Logs from './components/Logs';
import { useTaskStore } from './store/taskStore';
import * as api from './services/api';

function App() {
  const [worldObjects, setWorldObjects] = useState([]);
  const [backendStatus, setBackendStatus] = useState('checking');
  
  const world = useTaskStore((state) => state.world);
  const currentTask = useTaskStore((state) => state.currentTask);
  const ui = useTaskStore((state) => state.ui);
  const setLoading = useTaskStore((state) => state.setLoading);
  const setError = useTaskStore((state) => state.setError);
  const setWorld = useTaskStore((state) => state.setWorld);
  const setSelectedTab = useTaskStore((state) => state.setSelectedTab);

  // ===== INITIALIZATION =====

  /**
   * Check if backend is running on startup
   */
  useEffect(() => {
    const checkBackend = async () => {
      try {
        const response = await api.checkHealth();
        if (response.status === 'healthy') {
          setBackendStatus('connected');
          console.log('✓ Backend connected');
        } else {
          setBackendStatus('error');
          setError('Backend returned unexpected response');
        }
      } catch (error) {
        setBackendStatus('disconnected');
        setError('Cannot connect to backend. Is it running on http://localhost:8000?');
      }
    };

    checkBackend();
  }, [setError]);

  /**
   * Load initial world state on mount
   */
  useEffect(() => {
    const loadWorldState = async () => {
      try {
        const response = await api.getWorldStatus();
        if (response.status === 'success') {
          setWorld(response.world);
        }
      } catch (error) {
        console.error('Error loading world state:', error);
      }
    };

    if (backendStatus === 'connected') {
      loadWorldState();
    }
  }, [backendStatus, setWorld]);

  // ===== WORLD SETUP =====

  /**
   * Handle setting up world objects
   * Called from ControlPanel when user submits objects
   */
  const handleSetupWorld = async (objects) => {
    setLoading(true);
    try {
      const response = await api.setupWorld(objects);
      if (response.status === 'success') {
        setWorldObjects(objects);
        setWorld(response.world_status);
        console.log('✓ World setup complete');
      } else {
        setError(response.message || 'Failed to setup world');
      }
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Handle starting a task
   * Called from ControlPanel when user clicks "Start Task"
   */
  const handleStartTask = async (taskDescription, maxSteps) => {
    setLoading(true);
    try {
      const response = await api.startTask(taskDescription, maxSteps);
      if (response.status === 'success') {
        const result = response.task_result;
        console.log('✓ Task completed:', result);
        
        // Update store with results
        useTaskStore.setState({
          currentTask: {
            ...currentTask,
            id: result.session_id,
            description: taskDescription,
            status: result.success ? 'completed' : 'failed',
            steps_taken: result.steps_taken,
          },
          taskResults: result,
        });

        // Auto-switch to dashboard
        setSelectedTab('dashboard');
      } else {
        setError(response.message || 'Failed to start task');
      }
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  // ===== RENDER =====

  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <div className="header-content">
          <h1>🤖 LLM Agent in Virtual World</h1>
          <div className="header-status">
            <span className={`status-indicator ${backendStatus}`}>
              {backendStatus === 'connected' ? '🟢' : '🔴'} 
              {backendStatus === 'connected' ? 'Backend Connected' : 'Backend Disconnected'}
            </span>
          </div>
        </div>
      </header>

      {/* Error Display */}
      {ui.error && (
        <div className="error-banner">
          <strong>Error:</strong> {ui.error}
          <button 
            onClick={() => setError(null)}
            className="error-close"
          >
            ✕
          </button>
        </div>
      )}

      {/* Main Content */}
      <main className="app-main">
        {/* Left Panel - Controls */}
        <aside className="control-panel-container">
          <ControlPanel
            onSetupWorld={handleSetupWorld}
            onStartTask={handleStartTask}
            isLoading={ui.isLoading}
            backendConnected={backendStatus === 'connected'}
          />
        </aside>

        {/* Center - Main View */}
        <section className="viewport-container">
          <div className="tabs">
            <button
              className={`tab ${ui.selectedTab === 'viewport' ? 'active' : ''}`}
              onClick={() => setSelectedTab('viewport')}
            >
              3D Viewport
            </button>
            <button
              className={`tab ${ui.selectedTab === 'dashboard' ? 'active' : ''}`}
              onClick={() => setSelectedTab('dashboard')}
            >
              Results
            </button>
          </div>

          <div className="tab-content">
            {ui.selectedTab === 'viewport' && (
              <Viewport3D worldObjects={worldObjects} />
            )}
            {ui.selectedTab === 'dashboard' && (
              <Dashboard />
            )}
          </div>
        </section>

        {/* Right Panel - Logs */}
        {ui.showLogs && (
          <aside className="logs-container">
            <Logs />
          </aside>
        )}
      </main>

      {/* Loading Indicator */}
      {ui.isLoading && (
        <div className="loading-overlay">
          <div className="spinner"></div>
          <p>Processing...</p>
        </div>
      )}
    </div>
  );
}

export default App;