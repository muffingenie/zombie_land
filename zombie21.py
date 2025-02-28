import random
import json
import math
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

app = FastAPI()

##########################################################################
#                        PAGE HTML & JS                                   #
##########################################################################
html_content = """
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <title>Ville 3D - Vue Première Personne</title>
  <style>
    body {
      margin: 0;
      overflow: hidden;
      background: #ECEFF1;
      font-family: Arial, sans-serif;
    }
    #info {
      position: absolute; 
      top: 10px; 
      left: 10px;
      color: #263238; 
      background: rgba(255,255,255,0.8);
      padding: 8px; 
      border-radius: 5px;
      z-index: 2;
    }
    #gameOverMessage {
      display: none;
      position: absolute;
      top: 50%; 
      left: 50%;
      transform: translate(-50%, -50%);
      font-size: 48px;
      color: #D32F2F;
      background: rgba(255,255,255,0.9);
      padding: 20px;
      border-radius: 10px;
      z-index: 3;
    }
  </style>
</head>
<body>
  <div id="info">
    <b>Contrôles :</b><br/>
    - Flèches Gauche/Droite : tourner<br/>
    - Flèches Haut/Bas : avancer/reculer<br/>
    Rôle : <span id="roleLabel"></span><br/>
    Score : <span id="scoreLabel"></span>
  </div>
  <div id="gameOverMessage">GAME OVER</div>

  <!-- Inclusion de Three.js -->
  <script src="https://cdn.jsdelivr.net/npm/three@0.146.0/build/three.min.js"></script>
  
  <script>
  ///////////////////////////////
  //    Modèles de personnages  //
  ///////////////////////////////
  function createZombieModel() {
      const group = new THREE.Group();
      // Tête
      const headGeo = new THREE.SphereGeometry(1, 16, 16);
      const headMat = new THREE.MeshStandardMaterial({ color: 0x006400 });
      const head = new THREE.Mesh(headGeo, headMat);
      head.position.set(0, 2.5, 0);
      group.add(head);
      // Corps
      const bodyGeo = new THREE.CylinderGeometry(1, 1, 3, 16);
      const bodyMat = new THREE.MeshStandardMaterial({ color: 0x555555 });
      const body = new THREE.Mesh(bodyGeo, bodyMat);
      body.position.set(0, 1, 0);
      group.add(body);
      // Bras
      const armGeo = new THREE.CylinderGeometry(0.3, 0.3, 2, 12);
      const armMat = new THREE.MeshStandardMaterial({ color: 0x555555 });
      const leftArm = new THREE.Mesh(armGeo, armMat);
      leftArm.rotation.z = Math.PI / 2;
      leftArm.position.set(-1.3, 1.5, 0);
      group.add(leftArm);
      const rightArm = leftArm.clone();
      rightArm.position.set(1.3, 1.5, 0);
      group.add(rightArm);
      // Jambes
      const legGeo = new THREE.CylinderGeometry(0.4, 0.4, 2.5, 12);
      const legMat = new THREE.MeshStandardMaterial({ color: 0x333333 });
      const leftLeg = new THREE.Mesh(legGeo, legMat);
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
      const headGeo = new THREE.SphereGeometry(1, 16, 16);
      const headMat = new THREE.MeshStandardMaterial({ color: 0xFAD6A5 });
      const head = new THREE.Mesh(headGeo, headMat);
      head.position.set(0, 2.5, 0);
      group.add(head);
      // Corps
      const bodyGeo = new THREE.CylinderGeometry(1, 1, 3, 16);
      const bodyMat = new THREE.MeshStandardMaterial({ color: 0x87CEFA });
      const body = new THREE.Mesh(bodyGeo, bodyMat);
      body.position.set(0, 1, 0);
      group.add(body);
      // Bras
      const armGeo = new THREE.CylinderGeometry(0.3, 0.3, 2, 12);
      const armMat = new THREE.MeshStandardMaterial({ color: 0x87CEFA });
      const leftArm = new THREE.Mesh(armGeo, armMat);
      leftArm.rotation.z = Math.PI / 2;
      leftArm.position.set(-1.3, 1.5, 0);
      group.add(leftArm);
      const rightArm = leftArm.clone();
      rightArm.position.set(1.3, 1.5, 0);
      group.add(rightArm);
      // Jambes
      const legGeo = new THREE.CylinderGeometry(0.4, 0.4, 2.5, 12);
      const legMat = new THREE.MeshStandardMaterial({ color: 0x000080 });
      const leftLeg = new THREE.Mesh(legGeo, legMat);
      leftLeg.position.set(-0.5, -1, 0);
      group.add(leftLeg);
      const rightLeg = leftLeg.clone();
      rightLeg.position.set(0.5, -1, 0);
      group.add(rightLeg);
      return group;
  }

  ///////////////////////////////
  //    Variables globales     //
  ///////////////////////////////
  let scene, camera, renderer;
  let directionalLight, ambientLight;
  let clock;
  
  // État multijoueur
  let localPlayerId = null;
  let playersState = {};
  let playersMeshes = {};

  ///////////////////////////////
  //   Initialisation 3D       //
  ///////////////////////////////
  function initScene() {
      scene = new THREE.Scene();
      scene.background = new THREE.Color(0xB3E5FC);
      scene.fog = new THREE.FogExp2(0xB3E5FC, 0.002);

      // La caméra sera positionnée en "première personne" dans animate()
      camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 1, 2000);
      camera.position.set(200, 5, 200);

      renderer = new THREE.WebGLRenderer({ antialias: true });
      renderer.setSize(window.innerWidth, window.innerHeight);
      renderer.shadowMap.enabled = true;
      document.body.appendChild(renderer.domElement);

      clock = new THREE.Clock();

      // Lumières
      ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
      scene.add(ambientLight);

      directionalLight = new THREE.DirectionalLight(0xffffff, 0.9);
      directionalLight.position.set(300, 400, 200);
      directionalLight.castShadow = true;
      directionalLight.shadow.mapSize.width = 2048;
      directionalLight.shadow.mapSize.height = 2048;
      directionalLight.shadow.camera.near = 0.5;
      directionalLight.shadow.camera.far = 2000;
      scene.add(directionalLight);

      ////////////////////////////////////////
      //   Création du sol (zone 0..400)     //
      ////////////////////////////////////////
      const groundGeometry = new THREE.PlaneGeometry(400, 400);
      groundGeometry.rotateX(-Math.PI / 2);
      groundGeometry.translate(200, 0, 200);
      const groundMaterial = new THREE.MeshStandardMaterial({ color: 0x66BB6A });
      const ground = new THREE.Mesh(groundGeometry, groundMaterial);
      ground.receiveShadow = true;
      scene.add(ground);

      ////////////////////////////////////////
      //       Création des routes          //
      ////////////////////////////////////////
      const roadColor = 0x424242;
      // Routes verticales (positions x = 0, 40, …, 400)
      for (let i = 0; i <= 10; i++) {
          let roadGeom = new THREE.PlaneGeometry(4, 400);
          roadGeom.rotateX(-Math.PI / 2);
          roadGeom.translate(0, 0.05, 200);
          const roadMat = new THREE.MeshStandardMaterial({ color: roadColor });
          let road = new THREE.Mesh(roadGeom, roadMat);
          road.receiveShadow = true;
          road.position.set(i * 40, 0, 0);
          scene.add(road);
  
          // Passage piéton vertical
          let crossGeom = new THREE.PlaneGeometry(4, 2);
          crossGeom.rotateX(-Math.PI / 2);
          crossGeom.translate(0, 0.06, 200);
          let crossMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
          let cross = new THREE.Mesh(crossGeom, crossMat);
          cross.position.set(i * 40, 0, 0);
          scene.add(cross);
      }
      // Routes horizontales (positions z = 0, 40, …, 400)
      for (let j = 0; j <= 10; j++) {
          let roadGeom = new THREE.PlaneGeometry(400, 4);
          roadGeom.rotateX(-Math.PI / 2);
          roadGeom.translate(200, 0.05, 0);
          const roadMat = new THREE.MeshStandardMaterial({ color: roadColor });
          let road = new THREE.Mesh(roadGeom, roadMat);
          road.receiveShadow = true;
          road.position.set(0, 0, j * 40);
          scene.add(road);
  
          // Passage piéton horizontal
          let crossGeom = new THREE.PlaneGeometry(2, 4);
          crossGeom.rotateX(-Math.PI / 2);
          crossGeom.translate(200, 0.06, 0);
          let crossMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
          let cross = new THREE.Mesh(crossGeom, crossMat);
          cross.position.set(0, 0, j * 40);
          scene.add(cross);
      }
  
      ////////////////////////////////////////
      //    Chargement des immeubles        //
      ////////////////////////////////////////
      // Palette de couleurs pastel
      const buildingColors = ["#F8BBD0", "#CE93D8", "#B39DDB", "#9FA8DA", "#90CAF9", 
                              "#81D4FA", "#80DEEA", "#80CBC4", "#A5D6A7", "#C5E1A5"];
  
      fetch('/city')
        .then(response => response.json())
        .then(city => {
            city.buildings.forEach(b => {
                const geometry = new THREE.BoxGeometry(b.width, b.height, b.depth);
                const color = buildingColors[Math.floor(Math.random() * buildingColors.length)];
                const material = new THREE.MeshStandardMaterial({ color });
                const mesh = new THREE.Mesh(geometry, material);
                mesh.position.set(b.x, b.height/2, b.z);
                mesh.castShadow = true;
                mesh.receiveShadow = true;
                scene.add(mesh);
            });
            addStreetElements();
        });
  
      window.addEventListener('resize', onWindowResize, false);
  }
  
  ////////////////////////////////////////
  //   Éléments de rue (lampadaires, bancs, arbres)
  ////////////////////////////////////////
  function addStreetElements() {
      // Lampadaires placés au centre de chaque bloc (grille 10x10)
      for (let i = 0; i < 10; i++) {
          for (let j = 0; j < 10; j++) {
              const x = i * 40 + 20;
              const z = j * 40 + 20;
              const postGeom = new THREE.CylinderGeometry(0.1, 0.1, 10, 8);
              const postMat = new THREE.MeshStandardMaterial({ color: 0x424242 });
              const lampPost = new THREE.Mesh(postGeom, postMat);
              lampPost.position.set(x, 5, z);
              lampPost.castShadow = true;
              scene.add(lampPost);
  
              const lampHeadGeom = new THREE.SphereGeometry(0.5, 8, 8);
              const lampHeadMat = new THREE.MeshBasicMaterial({ color: 0xFFEB3B });
              const lampHead = new THREE.Mesh(lampHeadGeom, lampHeadMat);
              lampHead.position.set(x, 10, z);
              scene.add(lampHead);
          }
      }
      // Bancs : placés décalés dans chaque bloc
      for (let i = 0; i < 10; i++) {
          for (let j = 0; j < 10; j++) {
              const x = i * 40 + 28;
              const z = j * 40 + 10;
              const benchGeom = new THREE.BoxGeometry(4, 0.5, 1);
              const benchMat = new THREE.MeshStandardMaterial({ color: 0x8D6E63 });
              const bench = new THREE.Mesh(benchGeom, benchMat);
              bench.position.set(x, 0.3, z);
              bench.castShadow = true;
              scene.add(bench);
          }
      }
      // Arbres : position aléatoire dans la zone
      for (let i = 0; i < 50; i++) {
          const trunkGeom = new THREE.CylinderGeometry(0.5, 0.5, 5, 8);
          const trunkMat = new THREE.MeshStandardMaterial({ color: 0xA1887F });
          const trunk = new THREE.Mesh(trunkGeom, trunkMat);
          const foliageGeom = new THREE.SphereGeometry(3, 8, 8);
          const foliageMat = new THREE.MeshStandardMaterial({ color: 0x66BB6A });
          const foliage = new THREE.Mesh(foliageGeom, foliageMat);
  
          let x = Math.random() * 400;
          let z = Math.random() * 400;
          trunk.position.set(x, 2.5, z);
          foliage.position.set(x, 6, z);
          trunk.castShadow = true;
          foliage.castShadow = true;
          scene.add(trunk);
          scene.add(foliage);
      }
  }
  
  ////////////////////////////////////////
  //   Gestion du redimensionnement     //
  ////////////////////////////////////////
  function onWindowResize() {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
  }
  
  ////////////////////////////////////////
  //  Boucle d'animation et vue FPS     //
  ////////////////////////////////////////
  function animate() {
      requestAnimationFrame(animate);
  
      // Cycle jour/nuit (60 secondes)
      let elapsed = clock.getElapsedTime();
      let cycle = elapsed % 60;
      let intensity = 0.5 + 0.5 * Math.sin((cycle/60)*Math.PI*2);
      directionalLight.intensity = intensity;
      directionalLight.color.setRGB(1, intensity, intensity * 0.8);
  
      // Vue à la première personne : la caméra suit le joueur local
      if (localPlayerId && playersState[localPlayerId]) {
          const p = playersState[localPlayerId];
          camera.position.set(p.x, 5, p.z);
          const lookX = p.x + 50 * Math.sin(p.orientation);
          const lookZ = p.z + 50 * Math.cos(p.orientation);
          camera.lookAt(lookX, 5, lookZ);
  
          document.getElementById("roleLabel").textContent = (p.role === "zombie") ? "Zombie" : "Civil";
          document.getElementById("scoreLabel").textContent = p.score;
      }
  
      renderer.render(scene, camera);
  }
  
  ////////////////////////////////////////
  //     WebSocket / Multijoueur        //
  ////////////////////////////////////////
  function initWebSocket() {
      const ws = new WebSocket("ws://" + location.host + "/ws");
      ws.onopen = () => { console.log("Connecté au serveur WebSocket"); };
      ws.onmessage = (event) => {
          const data = JSON.parse(event.data);
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
                  let mesh = playersMeshes[p.id];
                  if (!mesh) {
                      if (p.role === "zombie") {
                          mesh = createZombieModel();
                      } else {
                          mesh = createCivilianModel();
                      }
                      mesh.castShadow = true;
                      playersMeshes[p.id] = mesh;
                      scene.add(mesh);
                  }
                  // Positionner le modèle de façon à ce que la base soit à y = 0
                  mesh.position.set(p.x, 0, p.z);
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
          } else if (event.key === "ArrowRight") {
              ws.send(JSON.stringify({ type: "rotate_right" }));
          } else if (event.key === "ArrowUp") {
              ws.send(JSON.stringify({ type: "forward" }));
          } else if (event.key === "ArrowDown") {
              ws.send(JSON.stringify({ type: "backward" }));
          }
      });
  }
  
  // Initialisation
  initScene();
  initWebSocket();
  animate();
  </script>
</body>
</html>
"""

##########################################################################
#                        Fonctions utilitaires                           #
##########################################################################
def building_bounding_box(b):
    x_min = b["x"] - b["width"] / 2
    x_max = b["x"] + b["width"] / 2
    z_min = b["z"] - b["depth"] / 2
    z_max = b["z"] + b["depth"] / 2
    return x_min, x_max, z_min, z_max

def building_on_road(b):
    """
    Vérifie si la bounding box de l'immeuble intersecte une route.
    Les routes se trouvent aux positions x et z multiples de 40,
    occupant une bande de ±2 unités autour de la position.
    """
    x_min, x_max, z_min, z_max = building_bounding_box(b)
    road_half = 2
    for r in range(0, 401, 40):
        if not (x_max < r - road_half or x_min > r + road_half):
            return True
    for r in range(0, 401, 40):
        if not (z_max < r - road_half or z_min > r + road_half):
            return True
    return False

def get_safe_spawn(city):
    """
    Renvoie un (x, z) aléatoire dans 0..400 qui n'est pas dans la bounding box d'un immeuble.
    """
    for _ in range(100):
        x = random.uniform(0, 400)
        z = random.uniform(0, 400)
        collision = False
        for b in city["buildings"]:
            bx_min, bx_max, bz_min, bz_max = building_bounding_box(b)
            if bx_min <= x <= bx_max and bz_min <= z <= bz_max:
                collision = True
                break
        if not collision:
            return x, z
    return 200, 200

##########################################################################
#                        Génération de la ville                          #
##########################################################################
def generate_city_layout():
    """
    Divise la zone 0..400 en une grille 20x20.
    Dans chaque bloc (taille 20x20), on essaie jusqu'à 5 fois de placer un immeuble
    dans une zone sûre (définie par une marge) et qui n'intersecte pas les routes.
    La probabilité de placement dans chaque bloc est de 90%.
    La hauteur des immeubles est tirée aléatoirement entre 10 et 50.
    """
    city = {"buildings": []}
    grid_x = 20
    grid_y = 20
    block_size = 400 / grid_x  # 20 unités par bloc
    margin = 2
    placement_probability = 0.9
    for i in range(grid_x):
        for j in range(grid_y):
            if random.random() < placement_probability:
                placed = False
                attempts = 0
                while not placed and attempts < 5:
                    attempts += 1
                    width = random.uniform(2, block_size - 2 * margin)
                    depth = random.uniform(2, block_size - 2 * margin)
                    height = random.uniform(10, 50)  # hauteur potentiellement plus élevée
                    safe_x_min = i * block_size + margin + width/2
                    safe_x_max = (i + 1) * block_size - margin - width/2
                    safe_z_min = j * block_size + margin + depth/2
                    safe_z_max = (j + 1) * block_size - margin - depth/2
                    if safe_x_min > safe_x_max or safe_z_min > safe_z_max:
                        continue
                    x = random.uniform(safe_x_min, safe_x_max)
                    z = random.uniform(safe_z_min, safe_z_max)
                    new_building = {"x": x, "z": z, "width": width, "depth": depth, "height": height}
                    if building_on_road(new_building):
                        continue
                    city["buildings"].append(new_building)
                    placed = True
    return city

city_layout = generate_city_layout()

##########################################################################
#                        Logique multijoueur                             #
##########################################################################
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

##########################################################################
#                           Routes FastAPI                               #
##########################################################################
@app.get("/")
async def get_index():
    return HTMLResponse(html_content)

@app.get("/city")
async def get_city():
    return JSONResponse(city_layout)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    player_id = str(id(websocket))
    # Probabilité initiale de zombie réduite à 5%
    role = "zombie" if random.random() < 0.05 else "civil"
    # Choisir une position de spawn sûre
    spawn_x, spawn_z = get_safe_spawn(city_layout)
    init_orientation = random.uniform(0, 2*math.pi)
    players[player_id] = {
        "id": player_id,
        "role": role,
        "x": spawn_x,
        "y": 0,
        "z": spawn_z,
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
  
            # Empêcher le déplacement si collision avec un immeuble
            if any(player["x"] >= b["x"] - b["width"]/2 and player["x"] <= b["x"] + b["width"]/2 and
                   player["z"] >= b["z"] - b["depth"]/2 and player["z"] <= b["z"] + b["depth"]/2
                   for b in city_layout["buildings"]):
                player["x"] = old_x
                player["z"] = old_z
  
            # Conversion zombie/civil avec probabilité de 5%
            if player["role"] == "zombie":
                for other in players.values():
                    if other["role"] == "civil" and check_collision_zombie(player, other):
                        if random.random() < 0.05:
                            other["role"] = "zombie"
                            player["score"] += 1
            elif player["role"] == "civil":
                for other in players.values():
                    if other["role"] == "zombie" and check_collision_zombie(player, other):
                        if random.random() < 0.05:
                            other["score"] += 1
                            player["role"] = "zombie"
                            break
  
            await broadcast_game_state()
  
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        if player_id in players:
            del players[player_id]
        await broadcast_game_state()

##########################################################################
#                             Lancement                                  #
##########################################################################
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
