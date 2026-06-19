// // ===== LOGS COMPONENT =====
 
// /**
//  * Logs Component
//  * 
//  * Shows real-time logs of what's happening
//  */
// export function Logs() {
//   const taskResults = useTaskStore((state) => state.taskResults);
//   const [logs, setLogs] = React.useState([]);
 
//   // Add logs when task changes
//   React.useEffect(() => {
//     if (taskResults) {
//       const newLogs = [
//         `Task started: "${taskResults.success ? 'Success' : 'Failed'}"`,
//         `Completed in ${taskResults.duration_seconds?.toFixed(2) || 'unknown'} seconds`,
//         `Steps taken: ${taskResults.steps_taken}`,
//       ];
//       setLogs(newLogs);
//     }
//   }, [taskResults]);
 
//   return (
//     <div className="logs">
//       <h3>📋 Logs</h3>
//       <div className="log-content">
//         {logs.length === 0 ? (
//           <p className="empty-logs">No logs yet. Start a task to see logs.</p>
//         ) : (
//           <ul className="log-list">
//             {logs.map((log, idx) => (
//               <li key={idx} className="log-entry">
//                 <span className="log-time">[{new Date().toLocaleTimeString()}]</span>
//                 <span className="log-message">{log}</span>
//               </li>
//             ))}
//           </ul>
//         )}
//       </div>
//     </div>
//   );
// }
 
// export default Dashboard;
 



// frontend/src/components/Logs.jsx

import React from 'react';
import { useTaskStore } from '../store/taskStore';
import '../styles/Logs.css';

function Logs() {
  const taskResults = useTaskStore((state) => state.taskResults);
  const [logs, setLogs] = React.useState([]);

  // Add logs when task changes
  React.useEffect(() => {
    if (taskResults) {
      const newLogs = [
        `Task started: "${taskResults.success ? 'Success' : 'Failed'}"`,
        `Completed in ${
          taskResults.duration_seconds?.toFixed(2) || 'unknown'
        } seconds`,
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
          <p className="empty-logs">
            No logs yet. Start a task to see logs.
          </p>
        ) : (
          <ul className="log-list">
            {logs.map((log, idx) => (
              <li key={idx} className="log-entry">
                <span className="log-time">
                  [{new Date().toLocaleTimeString()}]
                </span>

                <span className="log-message">{log}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export default Logs;