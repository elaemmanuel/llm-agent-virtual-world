// frontend/src/components/ControlPanel.jsx
/**
 * Control Panel Component
 * 
 * Allows user to:
 * - Set up world objects (cubes, doors, keys)
 * - Input task description
 * - Start agent task
 * - Monitor progress
 */

import React, { useState } from 'react';
import '../styles/ControlPanel.css';

function ControlPanel({ onSetupWorld, onStartTask, isLoading, backendConnected }) {
  const [setupMode, setSetupMode] = useState('world'); // world or task
  const [objects, setObjects] = useState([]);
  const [currentObject, setCurrentObject] = useState({
    id: 1,
    name: 'Object 1',
    object_type: 'cube',
    position: [5, 0, 5],
    color: 'red',
    pickupable: true,
    interactable: false,
  });
  const [taskDescription, setTaskDescription] = useState('');
  const [maxSteps, setMaxSteps] = useState(100);

  // ===== WORLD SETUP =====

  const handleAddObject = () => {
    if (!currentObject.name.trim()) {
      alert('Please enter an object name');
      return;
    }

    const newObject = {
      ...currentObject,
      id: objects.length + 1,
    };

    setObjects([...objects, newObject]);

    // Reset form
    setCurrentObject({
      id: objects.length + 2,
      name: `Object ${objects.length + 2}`,
      object_type: 'cube',
      position: [5 + objects.length, 0, 5],
      color: 'red',
      pickupable: true,
      interactable: false,
    });
  };

  const handleRemoveObject = (index) => {
    setObjects(objects.filter((_, i) => i !== index));
  };

  const handleSetupWorld = async () => {
    if (objects.length === 0) {
      alert('Please add at least one object');
      return;
    }

    await onSetupWorld(objects);
    setSetupMode('task');
  };

  const handlePositionChange = (axis, value) => {
    const newPosition = [...currentObject.position];
    newPosition[axis] = parseFloat(value) || 0;
    setCurrentObject({
      ...currentObject,
      position: newPosition,
    });
  };

  // ===== TASK EXECUTION =====

  const handleStartTask = async () => {
    if (!taskDescription.trim()) {
      alert('Please enter a task description');
      return;
    }

    if (objects.length === 0) {
      alert('Please set up the world first');
      return;
    }

    await onStartTask(taskDescription, maxSteps);
  };

  // ===== RENDER =====

  return (
    <div className="control-panel">
      <h2>🎮 Control Panel</h2>

      {!backendConnected && (
        <div className="status-warning">
          ⚠️ Backend not connected. Is it running?
        </div>
      )}

      {/* MODE SELECTOR */}
      <div className="mode-selector">
        <button
          className={`mode-btn ${setupMode === 'world' ? 'active' : ''}`}
          onClick={() => setSetupMode('world')}
        >
          🌍 World Setup
        </button>
        <button
          className={`mode-btn ${setupMode === 'task' ? 'active' : ''}`}
          onClick={() => setSetupMode('task')}
        >
          🎯 Task
        </button>
      </div>

      {/* WORLD SETUP MODE */}
      {setupMode === 'world' && (
        <div className="setup-world">
          <h3>Add Objects to World</h3>

          {/* OBJECT FORM */}
          <div className="form-group">
            <label>Object Name:</label>
            <input
              type="text"
              value={currentObject.name}
              onChange={(e) =>
                setCurrentObject({ ...currentObject, name: e.target.value })
              }
              placeholder="e.g., Red Cube"
            />
          </div>

          <div className="form-group">
            <label>Type:</label>
            <select
              value={currentObject.object_type}
              onChange={(e) =>
                setCurrentObject({ ...currentObject, object_type: e.target.value })
              }
            >
              <option value="cube">Cube</option>
              <option value="sphere">Sphere</option>
              <option value="door">Door</option>
              <option value="key">Key</option>
            </select>
          </div>

          <div className="form-group">
            <label>Color:</label>
            <select
              value={currentObject.color}
              onChange={(e) =>
                setCurrentObject({ ...currentObject, color: e.target.value })
              }
            >
              <option value="red">Red</option>
              <option value="blue">Blue</option>
              <option value="green">Green</option>
              <option value="yellow">Yellow</option>
              <option value="orange">Orange</option>
              <option value="purple">Purple</option>
            </select>
          </div>

          <div className="position-group">
            <label>Position (X, Y, Z):</label>
            <div className="position-inputs">
              <input
                type="number"
                value={currentObject.position[0]}
                onChange={(e) => handlePositionChange(0, e.target.value)}
                placeholder="X"
              />
              <input
                type="number"
                value={currentObject.position[1]}
                onChange={(e) => handlePositionChange(1, e.target.value)}
                placeholder="Y"
              />
              <input
                type="number"
                value={currentObject.position[2]}
                onChange={(e) => handlePositionChange(2, e.target.value)}
                placeholder="Z"
              />
            </div>
          </div>

          <div className="checkbox-group">
            <label>
              <input
                type="checkbox"
                checked={currentObject.pickupable}
                onChange={(e) =>
                  setCurrentObject({
                    ...currentObject,
                    pickupable: e.target.checked,
                  })
                }
              />
              Pickupable
            </label>
            <label>
              <input
                type="checkbox"
                checked={currentObject.interactable}
                onChange={(e) =>
                  setCurrentObject({
                    ...currentObject,
                    interactable: e.target.checked,
                  })
                }
              />
              Interactable
            </label>
          </div>

          <button onClick={handleAddObject} className="btn-secondary">
            + Add Object
          </button>

          {/* OBJECT LIST */}
          {objects.length > 0 && (
            <div className="object-list">
              <h4>Objects ({objects.length}):</h4>
              {objects.map((obj, idx) => (
                <div key={idx} className="object-item">
                  <div className="object-info">
                    <span className="object-name">{obj.name}</span>
                    <span className="object-type">{obj.object_type}</span>
                    <span className="object-color" style={{ color: obj.color }}>
                      ●
                    </span>
                  </div>
                  <button
                    onClick={() => handleRemoveObject(idx)}
                    className="btn-remove"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          )}

          <button
            onClick={handleSetupWorld}
            disabled={isLoading || objects.length === 0}
            className="btn-primary"
          >
            {isLoading ? '⏳ Setting up...' : '✓ Setup World'}
          </button>
        </div>
      )}

      {/* TASK MODE */}
      {setupMode === 'task' && (
        <div className="task-control">
          <h3>Configure Task</h3>

          <div className="form-group">
            <label>Task Description:</label>
            <textarea
              value={taskDescription}
              onChange={(e) => setTaskDescription(e.target.value)}
              placeholder="e.g., Navigate to the red cube and examine it"
              rows="4"
            />
          </div>

          <div className="form-group">
            <label>Max Steps:</label>
            <input
              type="number"
              value={maxSteps}
              onChange={(e) => setMaxSteps(parseInt(e.target.value) || 100)}
              min="10"
              max="500"
            />
          </div>

          <button
            onClick={handleStartTask}
            disabled={
              isLoading || !backendConnected || !taskDescription.trim()
            }
            className="btn-primary btn-large"
          >
            {isLoading ? '⏳ Running...' : '▶ Start Task'}
          </button>

          <p className="hint">
            Task will run on backend. Watch the 3D viewport or Results tab for
            progress.
          </p>
        </div>
      )}
    </div>
  );
}

export default ControlPanel;