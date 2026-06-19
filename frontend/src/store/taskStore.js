// frontend/src/store/taskStore.js
/**
 * Zustand Store - Global State Management
 * 
 * Manages:
 * - Current task state
 * - World state (objects, agent position)
 * - Task history and results
 * - UI state (loading, errors, etc.)
 * 
 * Zustand is like Redux but much simpler.
 * No boilerplate, just define state and actions.
 */

import { create } from 'zustand';

export const useTaskStore = create((set, get) => ({
  // ===== WORLD STATE =====
  
  world: {
    agent_position: [10, 0, 10],
    agent_direction: 'north',
    agent_inventory: [],
    agent_health: 100,
    step_count: 0,
    num_objects: 0,
    world_size: { x: 20, y: 10, z: 20 },
    objects: [], // Array of world objects
  },
  
  setWorld: (world) => set({ world }),
  updateAgentPosition: (position) =>
    set((state) => ({
      world: { ...state.world, agent_position: position },
    })),
  updateAgentInventory: (inventory) =>
    set((state) => ({
      world: { ...state.world, agent_inventory: inventory },
    })),
  setWorldObjects: (objects) =>
    set((state) => ({
      world: { ...state.world, objects },
    })),

  // ===== TASK STATE =====
  
  currentTask: {
    id: null,
    description: '',
    status: 'idle', // idle, running, completed, failed
    progress: 0,
    startTime: null,
    endTime: null,
    steps_taken: 0,
    max_steps: 100,
  },
  
  setCurrentTask: (task) => set({ currentTask: task }),
  updateTaskStatus: (status) =>
    set((state) => ({
      currentTask: { ...state.currentTask, status },
    })),
  updateTaskProgress: (progress) =>
    set((state) => ({
      currentTask: { ...state.currentTask, progress },
    })),
  updateTaskSteps: (steps) =>
    set((state) => ({
      currentTask: { ...state.currentTask, steps_taken: steps },
    })),

  // ===== TASK RESULTS =====
  
  taskResults: null, // Store final results
  setTaskResults: (results) => set({ taskResults: results }),
  
  taskActions: [], // Store all actions taken
  setTaskActions: (actions) => set({ taskActions: actions }),

  // ===== OBSERVATION STATE =====
  
  currentObservation: null, // Latest observation from agent
  setObservation: (observation) => set({ currentObservation: observation }),

  // ===== UI STATE =====
  
  ui: {
    isLoading: false,
    error: null,
    selectedTab: 'viewport', // viewport, dashboard, logs
    showLogs: true,
  },
  
  setLoading: (isLoading) =>
    set((state) => ({
      ui: { ...state.ui, isLoading },
    })),
  setError: (error) =>
    set((state) => ({
      ui: { ...state.ui, error },
    })),
  setSelectedTab: (tab) =>
    set((state) => ({
      ui: { ...state.ui, selectedTab: tab },
    })),
  toggleLogs: () =>
    set((state) => ({
      ui: { ...state.ui, showLogs: !state.ui.showLogs },
    })),

  // ===== UTILITY ACTIONS =====
  
  /**
   * Reset all state to initial values
   */
  reset: () =>
    set({
      world: {
        agent_position: [10, 0, 10],
        agent_direction: 'north',
        agent_inventory: [],
        agent_health: 100,
        step_count: 0,
        num_objects: 0,
        world_size: { x: 20, y: 10, z: 20 },
        objects: [],
      },
      currentTask: {
        id: null,
        description: '',
        status: 'idle',
        progress: 0,
        startTime: null,
        endTime: null,
        steps_taken: 0,
        max_steps: 100,
      },
      taskResults: null,
      taskActions: [],
      currentObservation: null,
      ui: {
        isLoading: false,
        error: null,
        selectedTab: 'viewport',
        showLogs: true,
      },
    }),

  /**
   * Prepare for a new task run
   */
  startNewTask: (description, maxSteps = 100) =>
    set({
      currentTask: {
        id: null,
        description,
        status: 'running',
        progress: 0,
        startTime: new Date(),
        endTime: null,
        steps_taken: 0,
        max_steps: maxSteps,
      },
      taskResults: null,
      taskActions: [],
      ui: {
        isLoading: true,
        error: null,
        selectedTab: 'viewport',
        showLogs: true,
      },
    }),

  /**
   * Complete a task run
   */
  completeTask: (results) =>
    set((state) => ({
      currentTask: {
        ...state.currentTask,
        status: results.success ? 'completed' : 'failed',
        endTime: new Date(),
        steps_taken: results.steps_taken,
      },
      taskResults: results,
      ui: {
        ...state.ui,
        isLoading: false,
      },
    })),
}));

// ===== USAGE EXAMPLES =====

/*
// In a component:
import { useTaskStore } from '../store/taskStore';

function MyComponent() {
  // Get state
  const world = useTaskStore((state) => state.world);
  const currentTask = useTaskStore((state) => state.currentTask);
  const setLoading = useTaskStore((state) => state.setLoading);
  const updateAgentPosition = useTaskStore(
    (state) => state.updateAgentPosition
  );

  // Use state
  return (
    <div>
      Agent at: {world.agent_position.join(', ')}
      Task: {currentTask.description}
      
      <button onClick={() => {
        setLoading(true);
        // do something
      }}>
        Start Task
      </button>
    </div>
  );
}

// Start a new task:
const startNewTask = useTaskStore((state) => state.startNewTask);
startNewTask('Find the red cube', 50);

// Complete a task:
const completeTask = useTaskStore((state) => state.completeTask);
completeTask({
  success: true,
  steps_taken: 12,
  final_position: [5, 0, 5],
  inventory: ['Red Cube'],
});

// Reset everything:
const reset = useTaskStore((state) => state.reset);
reset();
*/