"""Inline spatial runtime used by the single-file HTML exporter."""

from __future__ import annotations


def spatial_runtime_script() -> str:
    """Return a small Three.js-compatible WebGL runtime for offline exports.

    The public surface intentionally mirrors the subset of Three.js used by the
    AlgoLab renderer: Scene, PerspectiveCamera, WebGLRenderer, simple geometry,
    materials, Mesh, Line, BufferGeometry, and Vector3.  Keeping it inline
    preserves the existing single-file HTML contract while giving the spatial
    target a real WebGL scene/camera/renderer path.
    """

    return r"""<script>
(function () {
  if (window.THREE && window.THREE.WebGLRenderer) {
    window.AlgoLabSpatialRuntime = { source: 'threejs' };
    return;
  }

  function hexToRgba(color, alpha) {
    const raw = String(color || '#94a3b8').replace('#', '');
    const full = raw.length === 3 ? raw.split('').map(c => c + c).join('') : raw.padEnd(6, '0').slice(0, 6);
    const value = parseInt(full, 16);
    return [((value >> 16) & 255) / 255, ((value >> 8) & 255) / 255, (value & 255) / 255, alpha ?? 1];
  }
  function compile(gl, type, source) {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(shader) || 'shader compile failed');
    return shader;
  }
  function program(gl) {
    const vertex = compile(gl, gl.VERTEX_SHADER, `
      attribute vec3 a_position;
      uniform float u_pointSize;
      void main() {
        gl_Position = vec4(a_position.xy, 0.0, 1.0);
        gl_PointSize = u_pointSize;
      }`);
    const fragment = compile(gl, gl.FRAGMENT_SHADER, `
      precision mediump float;
      uniform vec4 u_color;
      uniform float u_round;
      void main() {
        if (u_round > 0.5) {
          vec2 d = gl_PointCoord - vec2(0.5);
          if (dot(d, d) > 0.25) discard;
        }
        gl_FragColor = u_color;
      }`);
    const result = gl.createProgram();
    gl.attachShader(result, vertex);
    gl.attachShader(result, fragment);
    gl.linkProgram(result);
    if (!gl.getProgramParameter(result, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(result) || 'program link failed');
    return result;
  }

  class Vector3 {
    constructor(x = 0, y = 0, z = 0) { this.x = x; this.y = y; this.z = z; }
    set(x, y, z) { this.x = x; this.y = y; this.z = z; return this; }
    clone() { return new Vector3(this.x, this.y, this.z); }
  }
  class Scene {
    constructor() { this.children = []; }
    add(...items) { this.children.push(...items.filter(Boolean)); }
    clear() { this.children = []; }
  }
  class PerspectiveCamera {
    constructor(fov = 45, aspect = 1, near = 0.1, far = 100) {
      this.fov = fov; this.aspect = aspect; this.near = near; this.far = far;
      this.position = new Vector3(0, 0, 8);
      this.target = new Vector3(0, 0, 0);
    }
    lookAt(target) { this.target = target && target.clone ? target.clone() : new Vector3(); }
    updateProjectionMatrix() {}
  }
  class Geometry {
    constructor(kind, options = {}) { this.kind = kind; this.options = options; this.size = options.size || options.radius || 1; }
  }
  class SphereGeometry extends Geometry {
    constructor(radius = 1) { super('sphere', { radius, size: radius }); }
  }
  class BoxGeometry extends Geometry {
    constructor(width = 1, height = 1, depth = 1) { super('box', { width, height, depth, size: Math.max(width, height, depth) }); }
  }
  class CylinderGeometry extends Geometry {
    constructor(radiusTop = 1, radiusBottom = 1, height = 1) { super('cylinder', { radiusTop, radiusBottom, height, size: Math.max(radiusTop, radiusBottom, height * 0.35) }); }
  }
  class BufferGeometry {
    constructor() { this.points = []; }
    setFromPoints(points) { this.points = points; return this; }
  }
  class MeshBasicMaterial {
    constructor(options = {}) { this.color = options.color || '#94a3b8'; this.opacity = options.opacity ?? 1; }
  }
  class LineBasicMaterial extends MeshBasicMaterial {}
  class Mesh {
    constructor(geometry, material) {
      this.geometry = geometry; this.material = material;
      this.position = new Vector3();
      this.userData = {};
    }
  }
  class Line extends Mesh {}
  class WebGLRenderer {
    constructor(options = {}) {
      this.canvas = options.canvas || document.createElement('canvas');
      this.gl = this.canvas.getContext('webgl', { antialias: options.antialias !== false, preserveDrawingBuffer: true })
        || this.canvas.getContext('experimental-webgl', { preserveDrawingBuffer: true });
      if (!this.gl) throw new Error('WebGL unavailable');
      this.program = program(this.gl);
      this.positionLocation = this.gl.getAttribLocation(this.program, 'a_position');
      this.colorLocation = this.gl.getUniformLocation(this.program, 'u_color');
      this.pointSizeLocation = this.gl.getUniformLocation(this.program, 'u_pointSize');
      this.roundLocation = this.gl.getUniformLocation(this.program, 'u_round');
      this.buffer = this.gl.createBuffer();
      this.clearColor = [0.043, 0.071, 0.125, 1];
    }
    setPixelRatio() {}
    setClearColor(color, alpha = 1) { this.clearColor = hexToRgba(color, alpha); }
    setSize(width, height, updateStyle = true) {
      this.canvas.width = Math.max(1, Math.floor(width));
      this.canvas.height = Math.max(1, Math.floor(height));
      if (updateStyle) {
        this.canvas.style.width = `${this.canvas.width}px`;
        this.canvas.style.height = `${this.canvas.height}px`;
      }
      this.gl.viewport(0, 0, this.canvas.width, this.canvas.height);
    }
    render(scene, camera) {
      const gl = this.gl;
      gl.useProgram(this.program);
      gl.clearColor(this.clearColor[0], this.clearColor[1], this.clearColor[2], this.clearColor[3]);
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
      gl.bindBuffer(gl.ARRAY_BUFFER, this.buffer);
      gl.enableVertexAttribArray(this.positionLocation);
      gl.vertexAttribPointer(this.positionLocation, 3, gl.FLOAT, false, 0, 0);
      const lines = scene.children.filter(item => item instanceof Line);
      const meshes = scene.children.filter(item => !(item instanceof Line)).sort((a, b) => (a.position.z || 0) - (b.position.z || 0));
      for (const line of lines) this.drawLine(line, camera);
      for (const mesh of meshes) this.drawMesh(mesh, camera);
      gl.flush();
    }
    project(point, camera) {
      const aspect = Math.max(0.5, camera.aspect || 1);
      const depth = Math.max(1.3, camera.position.z - (point.z || 0));
      const scale = 7 / depth;
      return {
        x: Math.max(-1, Math.min(1, (point.x * scale) / (4.8 * aspect))),
        y: Math.max(-1, Math.min(1, (point.y * scale) / 3.25)),
        scale,
      };
    }
    drawLine(line, camera) {
      const points = (line.geometry && line.geometry.points) || [];
      if (points.length < 2) return;
      const a = this.project(points[0], camera);
      const b = this.project(points[1], camera);
      this.gl.bufferData(this.gl.ARRAY_BUFFER, new Float32Array([a.x, a.y, 0, b.x, b.y, 0]), this.gl.STREAM_DRAW);
      this.gl.uniform4fv(this.colorLocation, hexToRgba(line.material.color, line.material.opacity));
      this.gl.uniform1f(this.pointSizeLocation, 1);
      this.gl.uniform1f(this.roundLocation, 0);
      this.gl.drawArrays(this.gl.LINES, 0, 2);
    }
    drawMesh(mesh, camera) {
      const p = this.project(mesh.position, camera);
      const base = mesh.geometry && mesh.geometry.kind === 'box' ? 34 : 42;
      const size = Math.max(16, Math.min(78, base * (mesh.geometry?.size || 1) * (0.65 + p.scale * 0.35)));
      this.gl.bufferData(this.gl.ARRAY_BUFFER, new Float32Array([p.x, p.y, 0]), this.gl.STREAM_DRAW);
      this.gl.uniform4fv(this.colorLocation, hexToRgba(mesh.material.color, mesh.material.opacity));
      this.gl.uniform1f(this.pointSizeLocation, size);
      this.gl.uniform1f(this.roundLocation, mesh.geometry && mesh.geometry.kind === 'box' ? 0 : 1);
      this.gl.drawArrays(this.gl.POINTS, 0, 1);
    }
  }

  window.THREE = {
    Vector3,
    Scene,
    PerspectiveCamera,
    WebGLRenderer,
    SphereGeometry,
    BoxGeometry,
    CylinderGeometry,
    BufferGeometry,
    MeshBasicMaterial,
    LineBasicMaterial,
    Mesh,
    Line,
  };
  window.AlgoLabSpatialRuntime = { source: 'inline-three-compatible-webgl' };
})();
</script>"""
