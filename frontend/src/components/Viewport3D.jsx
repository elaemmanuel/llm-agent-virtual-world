// frontend/src/components/Viewport3D.jsx
/**
 * Viewport3D Component
 * 
 * Renders a 3D scene using Three.js showing:
 * - The virtual world (grid, boundaries)
 * - The agent (moving cube)
 * - World objects (cubes, doors, etc.)
 * 
 * Updates in real-time as the agent moves
 */

import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { useTaskStore } from '../store/taskStore';

function Viewport3D({ worldObjects }) {
  const containerRef = useRef(null);
  const sceneRef = useRef(null);
  const rendererRef = useRef(null);
  const agentMeshRef = useRef(null);
  const objectMeshesRef = useRef({});

  const world = useTaskStore((state) => state.world);

  // ===== INITIALIZATION =====

  useEffect(() => {
    if (!containerRef.current) return;

    // ===== SCENE SETUP =====

    // Create scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1a2e);
    sceneRef.current = scene;

    // ===== CAMERA =====

    const camera = new THREE.PerspectiveCamera(
      75,
      containerRef.current.clientWidth / containerRef.current.clientHeight,
      0.1,
      1000
    );
    camera.position.set(15, 25, 15);
    camera.lookAt(10, 0, 10);

    // ===== RENDERER =====

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(
      containerRef.current.clientWidth,
      containerRef.current.clientHeight
    );
    renderer.shadowMap.enabled = true;
    containerRef.current.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // ===== LIGHTING =====

    // Ambient light (overall illumination)
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambientLight);

    // Directional light (like sun)
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(20, 30, 20);
    directionalLight.castShadow = true;
    directionalLight.shadow.mapSize.width = 2048;
    directionalLight.shadow.mapSize.height = 2048;
    directionalLight.shadow.camera.left = -30;
    directionalLight.shadow.camera.right = 30;
    directionalLight.shadow.camera.top = 30;
    directionalLight.shadow.camera.bottom = -30;
    scene.add(directionalLight);

    // ===== GROUND =====

    const groundGeometry = new THREE.PlaneGeometry(
      world.world_size.x,
      world.world_size.z
    );
    const groundMaterial = new THREE.MeshStandardMaterial({
      color: 0x2a4a2a,
      roughness: 0.8,
    });
    const ground = new THREE.Mesh(groundGeometry, groundMaterial);
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    scene.add(ground);

    // ===== GRID HELPER =====

    const gridHelper = new THREE.GridHelper(
      world.world_size.x,
      20,
      0x444444,
      0x333333
    );
    gridHelper.position.y = 0.01;
    scene.add(gridHelper);

    // ===== AGENT (CUBE) =====

    const agentGeometry = new THREE.BoxGeometry(0.8, 0.8, 0.8);
    const agentMaterial = new THREE.MeshStandardMaterial({
      color: 0x00ff00,
      emissive: 0x00aa00,
      roughness: 0.4,
    });
    const agent = new THREE.Mesh(agentGeometry, agentMaterial);
    agent.castShadow = true;
    agent.receiveShadow = true;
    agent.position.set(
      world.agent_position[0],
      0.4,
      world.agent_position[2]
    );
    scene.add(agent);
    agentMeshRef.current = agent;

    // Add arrow pointing forward on agent
    const arrowGeometry = new THREE.ConeGeometry(0.2, 0.4, 8);
    const arrowMaterial = new THREE.MeshStandardMaterial({ color: 0xffff00 });
    const arrow = new THREE.Mesh(arrowGeometry, arrowMaterial);
    arrow.position.z = -0.5;
    arrow.castShadow = true;
    agent.add(arrow);

    // ===== WORLD OBJECTS =====

    const createWorldObject = (obj) => {
      let geometry;
      const material = new THREE.MeshStandardMaterial({
        color: obj.color ? colorNameToHex(obj.color) : 0x8888ff,
        roughness: 0.6,
      });

      // Choose geometry based on type
      switch (obj.object_type) {
        case 'cube':
          geometry = new THREE.BoxGeometry(0.8, 0.8, 0.8);
          break;
        case 'sphere':
          geometry = new THREE.SphereGeometry(0.4, 32, 32);
          break;
        case 'door':
          geometry = new THREE.BoxGeometry(0.6, 1.5, 0.1);
          break;
        case 'key':
          geometry = new THREE.BoxGeometry(0.3, 0.3, 0.1);
          break;
        default:
          geometry = new THREE.BoxGeometry(0.5, 0.5, 0.5);
      }

      const mesh = new THREE.Mesh(geometry, material);
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      mesh.position.set(obj.position[0], obj.position[1] + 0.4, obj.position[2]);
      mesh.userData = obj;

      scene.add(mesh);
      return mesh;
    };

    // Add all world objects
    worldObjects.forEach((obj) => {
      const mesh = createWorldObject(obj);
      objectMeshesRef.current[obj.id] = mesh;
    });

    // ===== ANIMATION LOOP =====

    const animate = () => {
      requestAnimationFrame(animate);

      // Update agent position
      if (agentMeshRef.current) {
        agentMeshRef.current.position.x = world.agent_position[0];
        agentMeshRef.current.position.z = world.agent_position[2];
        agentMeshRef.current.position.y = 0.4;

        // Rotate agent to face direction
        const directionRotation = getDirectionRotation(world.agent_direction);
        agentMeshRef.current.rotation.y = directionRotation;
      }

      // Slight camera bob for depth perception
      camera.position.y = 25 + Math.sin(Date.now() / 3000) * 0.5;

      renderer.render(scene, camera);
    };
    animate();

    // ===== WINDOW RESIZE =====

    const handleResize = () => {
      if (!containerRef.current) return;
      const width = containerRef.current.clientWidth;
      const height = containerRef.current.clientHeight;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
    };

    window.addEventListener('resize', handleResize);

    // ===== CLEANUP =====

    return () => {
      window.removeEventListener('resize', handleResize);
      if (containerRef.current && renderer.domElement) {
        containerRef.current.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, [world]);

  // ===== UPDATE WORLD OBJECTS =====

  useEffect(() => {
    // Remove old objects
    Object.values(objectMeshesRef.current).forEach((mesh) => {
      sceneRef.current?.remove(mesh);
      mesh.geometry.dispose();
      mesh.material.dispose();
    });
    objectMeshesRef.current = {};

    // Add new objects
    worldObjects.forEach((obj) => {
      const geometry = getGeometryForType(obj.object_type);
      const material = new THREE.MeshStandardMaterial({
        color: obj.color ? colorNameToHex(obj.color) : 0x8888ff,
        roughness: 0.6,
      });

      const mesh = new THREE.Mesh(geometry, material);
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      mesh.position.set(obj.position[0], obj.position[1] + 0.4, obj.position[2]);
      mesh.userData = obj;

      sceneRef.current?.add(mesh);
      objectMeshesRef.current[obj.id] = mesh;
    });
  }, [worldObjects]);

  return (
    <div
      ref={containerRef}
      style={{
        width: '100%',
        height: '100%',
        borderRadius: '8px',
        overflow: 'hidden',
      }}
    />
  );
}

// ===== UTILITY FUNCTIONS =====

/**
 * Convert color name to hex
 */
function colorNameToHex(colorName) {
  const colors = {
    red: 0xff0000,
    green: 0x00ff00,
    blue: 0x0000ff,
    yellow: 0xffff00,
    cyan: 0x00ffff,
    magenta: 0xff00ff,
    white: 0xffffff,
    black: 0x000000,
    orange: 0xff8800,
    purple: 0x8800ff,
  };
  return colors[colorName.toLowerCase()] || 0x8888ff;
}

/**
 * Get rotation angle for direction
 */
function getDirectionRotation(direction) {
  const rotations = {
    north: 0,
    south: Math.PI,
    east: Math.PI / 2,
    west: (-Math.PI) / 2,
    up: 0,
    down: 0,
  };
  return rotations[direction] || 0;
}

/**
 * Get Three.js geometry for object type
 */
function getGeometryForType(objectType) {
  switch (objectType) {
    case 'cube':
      return new THREE.BoxGeometry(0.8, 0.8, 0.8);
    case 'sphere':
      return new THREE.SphereGeometry(0.4, 32, 32);
    case 'door':
      return new THREE.BoxGeometry(0.6, 1.5, 0.1);
    case 'key':
      return new THREE.BoxGeometry(0.3, 0.3, 0.1);
    default:
      return new THREE.BoxGeometry(0.5, 0.5, 0.5);
  }
}

export default Viewport3D;