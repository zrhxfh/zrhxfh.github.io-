<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>手机射击游戏</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            background: #111;
            overflow: hidden;
            font-family: Arial, sans-serif;
        }
        #gameCanvas {
            display: block;
            background: linear-gradient(to bottom, #001122, #003366);
            touch-action: none;
        }
        #ui {
            position: absolute;
            top: 10px;
            left: 10px;
            color: #fff;
            font-size: 18px;
            z-index: 10;
        }
        #gameOver {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            color: #fff;
            text-align: center;
            display: none;
            z-index: 20;
        }
        button {
            padding: 15px 30px;
            font-size: 18px;
            background: #ff6600;
            border: none;
            border-radius: 5px;
            margin-top: 20px;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <canvas id="gameCanvas"></canvas>
    <div id="ui">
        <div>分数: <span id="score">0</span></div>
        <div>生命: <span id="lives">3</span></div>
    </div>
    <div id="gameOver">
        <h2>游戏结束</h2>
        <p>最终分数: <span id="finalScore">0</span></p>
        <button onclick="restartGame()">重新开始</button>
    </div>

    <script>
        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');
        
        // 设置画布大小
        function resizeCanvas() {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        }
        resizeCanvas();
        window.addEventListener('resize', resizeCanvas);

        // 游戏状态
        let gameRunning = true;
        let score = 0;
        let lives = 3;
        
        // 玩家
        const player = {
            x: canvas.width / 2,
            y: canvas.height - 100,
            width: 50,
            height: 50,
            speed: 5,
            bullets: []
        };

        // 敌人数组
        let enemies = [];
        let enemySpeed = 2;
        
        // 触摸控制
        let touchX = null;
        canvas.addEventListener('touchstart', (e) => {
            touchX = e.touches[0].clientX;
        });
        
        canvas.addEventListener('touchmove', (e) => {
            if (touchX !== null) {
                const deltaX = e.touches[0].clientX - touchX;
                player.x += deltaX * 0.5;
                touchX = e.touches[0].clientX;
                
                // 边界限制
                player.x = Math.max(player.width/2, Math.min(canvas.width - player.width/2, player.x));
            }
            e.preventDefault();
        });
        
        canvas.addEventListener('touchend', () => {
            touchX = null;
            // 触摸结束时发射子弹
            if (gameRunning) {
                player.bullets.push({
                    x: player.x,
                    y: player.y - 20,
                    speed: 10,
                    width: 5,
                    height: 15
                });
            }
        });

        // 键盘控制（桌面端备用）
        const keys = {};
        window.addEventListener('keydown', (e) => {
            keys[e.key] = true;
            if (e.key === ' ' && gameRunning) {
                player.bullets.push({
                    x: player.x,
                    y: player.y - 20,
                    speed: 10,
                    width: 5,
                    height: 15
                });
            }
        });
        window.addEventListener('keyup', (e) => keys[e.key] = false);

        // 生成敌人
        function spawnEnemy() {
            enemies.push({
                x: Math.random() * (canvas.width - 40),
                y: -40,
                width: 40,
                height: 40,
                speed: enemySpeed + Math.random() * 2
            });
        }

        // 碰撞检测
        function checkCollision(rect1, rect2) {
            return rect1.x < rect2.x + rect2.width &&
                   rect1.x + rect1.width > rect2.x &&
                   rect1.y < rect2.y + rect2.height &&
                   rect1.y + rect1.height > rect2.y;
        }

        // 更新游戏
        function update() {
            if (!gameRunning) return;

            // 更新玩家位置（键盘控制）
            if (keys['ArrowLeft'] && player.x > player.width/2) {
                player.x -= player.speed;
            }
            if (keys['ArrowRight'] && player.x < canvas.width - player.width/2) {
                player.x += player.speed;
            }

            // 更新子弹
            player.bullets.forEach((bullet, bulletIndex) => {
                bullet.y -= bullet.speed;
                
                // 移除超出屏幕的子弹
                if (bullet.y + bullet.height < 0) {
                    player.bullets.splice(bulletIndex, 1);
                }

                // 检测子弹与敌人碰撞
                enemies.forEach((enemy, enemyIndex) => {
                    if (checkCollision(bullet, enemy)) {
                        player.bullets.splice(bulletIndex, 1);
                        enemies.splice(enemyIndex, 1);
                        score += 10;
                        document.getElementById('score').textContent = score;
                        
                        // 增加难度
                        if (score % 100 === 0) {
                            enemySpeed += 0.5;
                        }
                    }
                });
            });

            // 更新敌人
            enemies.forEach((enemy, index) => {
                enemy.y += enemy.speed;
                
                // 移除超出屏幕的敌人
                if (enemy.y > canvas.height) {
                    enemies.splice(index, 1);
                    lives--;
                    document.getElementById('lives').textContent = lives;
                    
                    if (lives <= 0) {
                        gameOver();
                    }
                }

                // 检测敌人与玩家碰撞
                if (checkCollision(enemy, player)) {
                    enemies.splice(index, 1);
                    lives--;
                    document.getElementById('lives').textContent = lives;
                    
                    if (lives <= 0) {
                        gameOver();
                    }
                }
            });

            // 随机生成敌人
            if (Math.random() < 0.02 + score * 0.0001) {
                spawnEnemy();
            }
        }

        // 渲染游戏
        function render() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // 绘制玩家（三角形飞船）
            ctx.fillStyle = '#00ff00';
            ctx.beginPath();
            ctx.moveTo(player.x, player.y - player.height/2);
            ctx.lineTo(player.x - player.width/2, player.y + player.height/2);
            ctx.lineTo(player.x + player.width/2, player.y + player.height/2);
            ctx.closePath();
            ctx.fill();
            
            // 绘制子弹
            ctx.fillStyle = '#ffff00';
            player.bullets.forEach(bullet => {
                ctx.fillRect(bullet.x - bullet.width/2, bullet.y, bullet.width, bullet.height);
            });
            
            // 绘制敌人（红色方块）
            ctx.fillStyle = '#ff0000';
            enemies.forEach(enemy => {
                ctx.fillRect(enemy.x, enemy.y, enemy.width, enemy.height);
            });
        }

        // 游戏循环
        function gameLoop() {
            update();
            render();
            requestAnimationFrame(gameLoop);
        }

        // 游戏结束
        function gameOver() {
            gameRunning = false;
            document.getElementById('finalScore').textContent = score;
            document.getElementById('gameOver').style.display = 'block';
        }

        // 重新开始
        function restartGame() {
            score = 0;
            lives = 3;
            gameRunning = true;
            enemies = [];
            player.bullets = [];
            player.x = canvas.width / 2;
            enemySpeed = 2;
            
            document.getElementById('score').textContent = score;
            document.getElementById('lives').textContent = lives;
            document.getElementById('gameOver').style.display = 'none';
        }

        // 启动游戏
        gameLoop();
    </script>
</body>
</html>

