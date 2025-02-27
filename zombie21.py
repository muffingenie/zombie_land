import random
import json
import math
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

app = FastAPI()
# Monter le dossier statique (vérifiez le chemin)
app.mount("/static", StaticFiles(directory="/home/mufffin/Desktop/game/static"), name="static")

html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Zombie City - First Person with Scoring</title>
    <style>
        body { margin: 0; overflow: hidden; }
        #info {
            position: absolute; top: 10px; left: 10px;
            color: white; background: rgba(0,0,0,0.5);
            padding: 5px; border-radius: 5px;
            z-index: 2;
        }
        #roleLabel {
            margin-top: 5px;
            display: block;
        }
        #gameOverMessage {
            display: none;
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 48px;
            color: red;
            background: rgba(0,0,0,0.7);
            padding: 20px;
            border-radius: 10px;
            z-index: 3;
        }
        #scoreLabel {
            margin-top: 5px;
            display: block;
        }
    </style>
</head>
<body>
<div id="info">
    <b>Contrôles :</b><br/>
    - Flèche gauche/droite : tourner<br/>
    - Flèche haut/bas : avancer/reculer<br/>
    - Vue à la première personne (vous ne voyez pas votre propre modèle)<br/>
    - Zombies infectent Civils<br/>
    Rôle : <span id="roleLabel"></span><br/>
    Score : <span id="scoreLabel"></span>
</div>
<div id="gameOverMessage">ZOMBIES WON</div>

<!-- Three.js -->
<script src="https://cdn.jsdelivr.net/npm/three@0.128.0/build/three.min.js"></script>

<script>
// --- Fonctions pour créer les modèles simples ---
function createZombieModel() {
    const group = new THREE.Group();
    // Tête
    const headGeometry = new THREE.SphereGeometry(1, 16, 16);
    const headMaterial = new THREE.MeshStandardMaterial({ color: 0x006400 });
    const head = new THREE.Mesh(headGeometry, headMaterial);
    head.position.set(0, 2.5, 0);
    group.add(head);
    // Corps
    const bodyGeometry = new THREE.CylinderGeometry(1, 1, 3, 16);
    const bodyMaterial = new THREE.MeshStandardMaterial({ color: 0x555555 });
    const body = new THREE.Mesh(bodyGeometry, bodyMaterial);
    body.position.set(0, 1, 0);
    group.add(body);
    // Bras
    const armGeometry = new THREE.CylinderGeometry(0.3, 0.3, 2, 12);
    const armMaterial = new THREE.MeshStandardMaterial({ color: 0x555555 });
    const leftArm = new THREE.Mesh(armGeometry, armMaterial);
    leftArm.rotation.z = Math.PI / 2;
    leftArm.position.set(-1.3, 1.5, 0);
    group.add(leftArm);
    const rightArm = leftArm.clone();
    rightArm.position.set(1.3, 1.5, 0);
    group.add(rightArm);
    // Jambes
    const legGeometry = new THREE.CylinderGeometry(0.4, 0.4, 2.5, 12);
    const legMaterial = new THREE.MeshStandardMaterial({ color: 0x333333 });
    const leftLeg = new THREE.Mesh(legGeometry, legMaterial);
    leftLeg.position.set(-0.5, -1, 0);
    group.add(leftLeg);
    const rightLeg = leftLeg.clone();
    rightLeg.position.set(0.5, -1, 0);
    group.add(rightLeg);
    return group;
}

function createCivilianModel() {
    const group = new THREE.Group();
    // Tête
    const headGeometry = new THREE.SphereGeometry(1, 16, 16);
    const headMaterial = new THREE.MeshStandardMaterial({ color: 0xFAD6A5 });
    const head = new THREE.Mesh(headGeometry, headMaterial);
    head.position.set(0, 2.5, 0);
    group.add(head);
    // Corps
    const bodyGeometry = new THREE.CylinderGeometry(1, 1, 3, 16);
    const bodyMaterial = new THREE.MeshStandardMaterial({ color: 0x87CEFA });
    const body = new THREE.Mesh(bodyGeometry, bodyMaterial);
    body.position.set(0, 1, 0);
    group.add(body);
    // Bras
    const armGeometry = new THREE.CylinderGeometry(0.3, 0.3, 2, 12);
    const armMaterial = new THREE.MeshStandardMaterial({ color: 0x87CEFA });
    const leftArm = new THREE.Mesh(armGeometry, armMaterial);
    leftArm.rotation.z = Math.PI / 2;
    leftArm.position.set(-1.3, 1.5, 0);
    group.add(leftArm);
    const rightArm = leftArm.clone();
    rightArm.position.set(1.3, 1.5, 0);
    group.add(rightArm);
    // Jambes
    const legGeometry = new THREE.CylinderGeometry(0.4, 0.4, 2.5, 12);
    const legMaterial = new THREE.MeshStandardMaterial({ color: 0x000080 });
    const leftLeg = new THREE.Mesh(legGeometry, legMaterial);
    leftLeg.position.set(-0.5, -1, 0);
    group.add(leftLeg);
    const rightLeg = leftLeg.clone();
    rightLeg.position.set(0.5, -1, 0);
    group.add(rightLeg);
    return group;
}

let zombieModelPrototype = createZombieModel();
let civilianModelPrototype = createCivilianModel();

let scene, camera, renderer;
let localPlayerId = null;
let playersState = {};  // état des joueurs (position, orientation, rôle, score)
let playersMeshes = {}; // modèles 3D clonés pour les autres joueurs

function initScene() {
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x87CEEB);
    scene.fog = new THREE.FogExp2(0x87CEEB, 0.002);
    camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 1, 2000);
    camera.position.set(0, 2, 0);
    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.shadowMap.enabled = true;
    document.body.appendChild(renderer.domElement);
    // Lumières
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
    scene.add(ambientLight);
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(300, 400, 200);
    directionalLight.castShadow = true;
    directionalLight.shadow.mapSize.width = 1024;
    directionalLight.shadow.mapSize.height = 1024;
    directionalLight.shadow.camera.near = 0.5;
    directionalLight.shadow.camera.far = 2000;
    scene.add(directionalLight);
    // Sol avec texture d'herbe
    const groundGeometry = new THREE.PlaneGeometry(400, 400);
    groundGeometry.rotateX(-Math.PI / 2);
    groundGeometry.translate(200, 0, 200);
    const groundMaterial = new THREE.MeshStandardMaterial({ color: 0x228B22 });
    const grassTextureLoader = new THREE.TextureLoader();
    grassTextureLoader.load("/static/grass.png", function(texture) {
        texture.wrapS = THREE.RepeatWrapping;
        texture.wrapT = THREE.RepeatWrapping;
        texture.repeat.set(10, 10);
        groundMaterial.map = texture;
        groundMaterial.needsUpdate = true;
    });
    const ground = new THREE.Mesh(groundGeometry, groundMaterial);
    ground.receiveShadow = true;
    scene.add(ground);
    // Routes avec texture road.png
    const roadTextureLoader = new THREE.TextureLoader();
    roadTextureLoader.load("/static/road.png", function(roadTexture) {
        roadTexture.wrapS = THREE.RepeatWrapping;
        roadTexture.wrapT = THREE.RepeatWrapping;
        // Routes verticales
        for (let i = 0; i <= 10; i++) {
            let roadGeom = new THREE.PlaneGeometry(4, 400);
            let roadMat = new THREE.MeshStandardMaterial({ map: roadTexture });
            roadMat.map.repeat.set(1, 10);
            roadMat.map.needsUpdate = true;
            let road = new THREE.Mesh(roadGeom, roadMat);
            road.rotation.x = -Math.PI / 2;
            road.position.set(i * 40, 0.01, 200);
            scene.add(road);
        }
        // Routes horizontales
        for (let j = 0; j <= 10; j++) {
            let roadGeom = new THREE.PlaneGeometry(400, 4);
            let roadMat = new THREE.MeshStandardMaterial({ map: roadTexture });
            roadMat.map.repeat.set(10, 1);
            roadMat.map.needsUpdate = true;
            let road = new THREE.Mesh(roadGeom, roadMat);
            road.rotation.x = -Math.PI / 2;
            road.position.set(200, 0.02, j * 40);
            scene.add(road);
        }
    });
    // Immeubles avec texture "building.png"
    const buildingTextureLoader = new THREE.TextureLoader();
    buildingTextureLoader.load("/static/building.png", function(buildingTexture) {
        buildingTexture.wrapS = THREE.RepeatWrapping;
        buildingTexture.wrapT = THREE.RepeatWrapping;
        fetch('/city')
          .then(response => response.json())
          .then(city => {
            city.buildings.forEach(b => {
              const geometry = new THREE.BoxGeometry(b.width, b.height, b.depth);
              const material = new THREE.MeshStandardMaterial({ map: buildingTexture });
              material.map.repeat.set(b.width/10, b.height/10);
              material.map.needsUpdate = true;
              const mesh = new THREE.Mesh(geometry, material);
              mesh.position.set(b.x, b.height / 2, b.z);
              mesh.castShadow = true;
              mesh.receiveShadow = true;
              scene.add(mesh);
            });
          });
    });
    window.addEventListener('resize', onWindowResize, false);
}

function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}

function initWebSocket() {
    const ws = new WebSocket("ws://" + location.host + "/ws");
    ws.onopen = () => { console.log("Connecté au serveur WebSocket"); };
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        // Condition de victoire
        if (data.gameOver) {
            document.getElementById("gameOverMessage").style.display = "block";
            document.getElementById("gameOverMessage").innerText = data.gameOver;
        } else {
            document.getElementById("gameOverMessage").style.display = "none";
        }
        if (data.type === "assign_id") {
            localPlayerId = data.player_id;
            return;
        }
        if (data.players) {
            data.players.forEach(p => { playersState[p.id] = p; });
            for (let pid in playersState) {
                if (!data.players.some(obj => obj.id === pid)) {
                    delete playersState[pid];
                }
            }
            data.players.forEach(p => {
                if (p.id === localPlayerId) {
                    document.getElementById("roleLabel").innerText = (p.role === "zombie") ? "Zombie" : "Civil";
                    document.getElementById("scoreLabel").innerText = "Score : " + p.score;
                    return;
                }
                let mesh = playersMeshes[p.id];
                if (!mesh || mesh.userData.role !== p.role) {
                    if (mesh) {
                        scene.remove(mesh);
                        delete playersMeshes[p.id];
                    }
                    mesh = (p.role === "zombie") ? zombieModelPrototype.clone() : civilianModelPrototype.clone();
                    mesh.userData.role = p.role;
                    mesh.traverse(child => {
                        if (child.isMesh) {
                            child.castShadow = true;
                            child.receiveShadow = true;
                        }
                    });
                    playersMeshes[p.id] = mesh;
                    scene.add(mesh);
                }
                mesh.position.set(p.x, p.y, p.z);
            });
            for (let pid in playersMeshes) {
                if (!data.players.some(obj => obj.id === pid)) {
                    scene.remove(playersMeshes[pid]);
                    delete playersMeshes[pid];
                }
            }
        }
    };
    document.addEventListener("keydown", (event) => {
        if (event.key === "ArrowLeft") {
            ws.send(JSON.stringify({ type: "rotate_left" }));
        }
        else if (event.key === "ArrowRight") {
            ws.send(JSON.stringify({ type: "rotate_right" }));
        }
        else if (event.key === "ArrowUp") {
            ws.send(JSON.stringify({ type: "forward" }));
        }
        else if (event.key === "ArrowDown") {
            ws.send(JSON.stringify({ type: "backward" }));
        }
    });
}

function animate() {
    requestAnimationFrame(animate);
    if (localPlayerId && playersState[localPlayerId]) {
        const p = playersState[localPlayerId];
        camera.position.set(p.x, p.y + 2, p.z);
        const lookX = p.x + 100 * Math.sin(p.orientation);
        const lookZ = p.z + 100 * Math.cos(p.orientation);
        camera.lookAt(lookX, p.y + 2, lookZ);
    }
    renderer.render(scene, camera);
}

initScene();
initWebSocket();
animate();
</script>
</body>
</html>
"""

def generate_city_layout():
    city = {"buildings": []}
    grid_size = 10
    block_size = 40
    # Augmenter la densité : probabilité de construction à 0.9
    for i in range(grid_size):
        for j in range(grid_size):
            if random.random() < 0.9:
                x = i * block_size + block_size/2 + random.uniform(-5, 5)
                z = j * block_size + block_size/2 + random.uniform(-5, 5)
                width = random.uniform(5, 15)
                depth = random.uniform(5, 15)
                height = random.uniform(10, 50)
                city["buildings"].append({
                    "x": x,
                    "z": z,
                    "width": width,
                    "depth": depth,
                    "height": height
                })
    return city

city_layout = generate_city_layout()

def building_bounding_box(b):
    x_min = b["x"] - b["width"] / 2
    x_max = b["x"] + b["width"] / 2
    z_min = b["z"] - b["depth"] / 2
    z_max = b["z"] + b["depth"] / 2
    return x_min, x_max, z_min, z_max

def check_building_collision(x, z, city):
    for b in city["buildings"]:
        x_min, x_max, z_min, z_max = building_bounding_box(b)
        if x_min <= x <= x_max and z_min <= z <= z_max:
            return True
    return False

from fastapi import WebSocket
from fastapi.responses import HTMLResponse, JSONResponse

@app.get("/")
async def get_index():
    return HTMLResponse(html_content)

@app.get("/city")
async def get_city():
    return JSONResponse(city_layout)

players = {}

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    async def broadcast(self, message: str):
        for conn in self.active_connections:
            await conn.send_text(message)

manager = ConnectionManager()

def check_collision_zombie(p1, p2, threshold=5.0):
    dx = p1["x"] - p2["x"]
    dz = p1["z"] - p2["z"]
    return math.sqrt(dx*dx + dz*dz) < threshold

async def broadcast_game_state():
    state = {"players": list(players.values())}
    if state["players"] and all(p["role"] == "zombie" for p in state["players"]):
        state["gameOver"] = "ZOMBIES WON"
    await manager.broadcast(json.dumps(state))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    player_id = str(id(websocket))
    # Ajouter le score à 0 lors de la création du joueur
    role = "zombie" if not any(p["role"] == "zombie" for p in players.values()) else "survivor"
    init_x = random.uniform(0, 400)
    init_z = random.uniform(0, 400)
    init_orientation = random.uniform(0, 2*math.pi)
    players[player_id] = {
        "id": player_id,
        "role": role,
        "x": init_x,
        "y": 0,
        "z": init_z,
        "orientation": init_orientation,
        "score": 0
    }
    await websocket.send_json({"type": "assign_id", "player_id": player_id})
    await broadcast_game_state()
    try:
        while True:
            data_text = await websocket.receive_text()
            try:
                data = json.loads(data_text)
            except json.JSONDecodeError:
                continue
            player = players.get(player_id)
            if not player:
                continue
            old_x, old_z = player["x"], player["z"]
            rot_speed = 0.1
            move_speed = 2.0
            if data.get("type") == "rotate_left":
                player["orientation"] += rot_speed
            elif data.get("type") == "rotate_right":
                player["orientation"] -= rot_speed
            elif data.get("type") == "forward":
                player["x"] += move_speed * math.sin(player["orientation"])
                player["z"] += move_speed * math.cos(player["orientation"])
            elif data.get("type") == "backward":
                player["x"] -= move_speed * math.sin(player["orientation"])
                player["z"] -= move_speed * math.cos(player["orientation"])
            if check_building_collision(player["x"], player["z"], city_layout):
                player["x"] = old_x
                player["z"] = old_z
            
            if player["role"] == "zombie":
                for other in players.values():
                    if other["role"] == "survivor" and check_collision_zombie(player, other):
                        other["role"] = "zombie"
                        player["score"] += 1
            elif player["role"] == "survivor":
                for other in players.values():
                    if other["role"] == "zombie" and check_collision_zombie(player, other):
                        other["score"] += 1
                        player["role"] = "zombie"
                        break
            await broadcast_game_state()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        if player_id in players:
            del players[player_id]
        await broadcast_game_state()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
