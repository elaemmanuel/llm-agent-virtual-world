// frontend/src/components/Dashboard.jsx
/**
 * Dashboard Component
 * 
 * Displays task results:
 * - Success/failure status
 * - Steps taken
 * - Final inventory
 * - Performance metrics
 */

import React, { useEffect, useState } from 'react';
import { useTaskStore } from '../store/taskStore';
import * as api from '../services/api';
import '../styles/Dashboard.css';

function Dashboard() {
  const currentTask = useTaskStore((state) => state.currentTask);
  const taskResults = useTaskStore((state) => state.taskResults);
  const setTaskActions = useTaskStore((state) => state.setTaskActions);
  const [actions, setActions] = useState([]);
  const [loading, setLoading] = useState(false);

  // Fetch actions when task completes
  useEffect(() => {
    if (taskResults?.session_id) {
      const fetchActions = async () => {
        setLoading(true);
        try {
          const response = await api.getTaskActions(taskResults.session_id);
          if (response.status === 'success') {
            setActions(response.actions);
            setTaskActions(response.actions);
          }
        } catch (error) {
          console.error('Error fetching actions:', error);
        } finally {
          setLoading(false);
        }
      };

      fetchActions();
    }
  }, [taskResults, setTaskActions]);

  if (!taskResults) {
    return (
      <div className="dashboard empty">
        <p>No task has been run yet.</p>
        <p>Configure a task in the Control Panel and click "Start Task".</p>
      </div>
    );
  }

  const statusIcon = taskResults.success ? '✅' : '❌';
  const statusText = taskResults.success ? 'SUCCESS' : 'FAILED';

  return (
    <div className="dashboard">
      {/* RESULT SUMMARY */}
      <div className="result-summary">
        <h2>
          {statusIcon} Task {statusText}
        </h2>

        <div className="summary-grid">
          <div className="summary-item">
            <label>Task Description:</label>
            <p>{currentTask.description}</p>
          </div>

          <div className="summary-item">
            <label>Status:</label>
            <p className={`status ${taskResults.status}`}>
              {taskResults.status.toUpperCase()}
            </p>
          </div>

          <div className="summary-item">
            <label>Steps Taken:</label>
            <p>
              {taskResults.steps_taken} / {currentTask.max_steps}
            </p>
          </div>

          <div className="summary-item">
            <label>Duration:</label>
            <p>{taskResults.duration_seconds?.toFixed(2) || '—'} seconds</p>
          </div>

          <div className="summary-item">
            <label>Final Position:</label>
            <p>
              [{taskResults.final_position?.join(', ') || '—'}]
            </p>
          </div>

          <div className="summary-item">
            <label>Final Inventory:</label>
            <p>
              {taskResults.inventory && taskResults.inventory.length > 0
                ? taskResults.inventory.join(', ')
                : 'Empty'}
            </p>
          </div>
        </div>
      </div>

      {/* ACTION TIMELINE */}
      <div className="action-timeline">
        <h3>Action Timeline ({actions.length} steps)</h3>

        {loading && <p className="loading">Loading actions...</p>}

        {!loading && actions.length === 0 && (
          <p className="no-actions">No actions recorded</p>
        )}

        {!loading && actions.length > 0 && (
          <div className="timeline">
            {actions.map((action, idx) => (
              <div
                key={idx}
                className={`timeline-item ${action.success ? 'success' : 'failed'}`}
              >
                <div className="timeline-marker">
                  {action.success ? '✓' : '✗'}
                </div>
                <div className="timeline-content">
                  <div className="action-header">
                    <strong>Step {action.step_number}</strong>
                    <span className="action-type">{action.action_type}</span>
                    {action.success && <span className="badge success">OK</span>}
                    {!action.success && <span className="badge error">FAILED</span>}
                  </div>
                  <div className="action-details">
                    <p>{action.result_message}</p>
                    {action.position_before && action.position_after && (
                      <p className="positions">
                        {action.position_before.join(', ')} →{' '}
                        {action.position_after.join(', ')}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ===== LOGS COMPONENT =====

/**
 * Logs Component
 * 
 * Shows real-time logs of what's happening
 */
export function Logs() {
  const taskResults = useTaskStore((state) => state.taskResults);
  const [logs, setLogs] = React.useState([]);

  // Add logs when task changes
  React.useEffect(() => {
    if (taskResults) {
      const newLogs = [
        `Task started: "${taskResults.success ? 'Success' : 'Failed'}"`,
        `Completed in ${taskResults.duration_seconds?.toFixed(2) || 'unknown'} seconds`,
        `Steps taken: ${taskResults.steps_taken}`,
      ];
      setLogs(newLogs);
    }
  }, [taskResults]);

  return (
    <div className="logs">
      <h3>📋 Logs</h3>
      <div className="log-content">
        {logs.length === 0 ? (
          <p className="empty-logs">No logs yet. Start a task to see logs.</p>
        ) : (
          <ul className="log-list">
            {logs.map((log, idx) => (
              <li key={idx} className="log-entry">
                <span className="log-time">[{new Date().toLocaleTimeString()}]</span>
                <span className="log-message">{log}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default Dashboard;