import math
import sys
from dataclasses import dataclass

import pygame
from pygame.locals import DOUBLEBUF, OPENGL
from OpenGL.GL import *
from OpenGL.GLU import *

# ===== 全局参数 =====
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
FPS = 60

RESTITUTION = 0.55  # 弹性系数（碰撞反弹）
FRICTION = 0.985
GRAVITY = 30.0

BALL_RADIUS = 0.45
MAX_SPEED = 34.0
ACCELERATION = 22.0
BRAKE_ACCEL = 28.0
TURN_SPEED = 2.35  # rad/s

TRACK_HALF_WIDTH = 5.0
TRACK_LENGTH = 120.0


@dataclass
class Vec3:
    x: float
    y: float
    z: float

    def __add__(self, other):
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other):
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float):
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    def dot(self, other) -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def length(self) -> float:
        return math.sqrt(self.dot(self))

    def normalized(self):
        l = self.length()
        if l < 1e-8:
            return Vec3(0.0, 0.0, 0.0)
        return self * (1.0 / l)


@dataclass
class Ball:
    pos: Vec3
    vel: Vec3
    yaw: float


class Track:
    def ground_height(self, z: float) -> float:
        # 平地 -> 斜坡上升 -> 平台 -> 斜坡下降
        if z < 26.0:
            return 0.0
        if z < 46.0:
            return (z - 26.0) * 0.28
        if z < 66.0:
            return 5.6
        if z < 86.0:
            return 5.6 - (z - 66.0) * 0.28
        return 0.0

    def on_track(self, x: float, z: float) -> bool:
        return abs(x) <= TRACK_HALF_WIDTH and 0.0 <= z <= TRACK_LENGTH


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), DOUBLEBUF | OPENGL)
        pygame.display.set_caption("PyOpenGL Racing Sphere")

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_COLOR_MATERIAL)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_POSITION, (35.0, 40.0, 15.0, 1.0))
        glLightfv(GL_LIGHT0, GL_DIFFUSE, (0.95, 0.95, 0.95, 1.0))

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(65.0, WINDOW_WIDTH / WINDOW_HEIGHT, 0.1, 400.0)
        glMatrixMode(GL_MODELVIEW)

        self.clock = pygame.time.Clock()
        self.track = Track()
        self.ball = Ball(pos=Vec3(0.0, BALL_RADIUS, 2.0), vel=Vec3(0.0, 0.0, 0.0), yaw=0.0)
        self.running = True

    def handle_input(self, dt: float):
        keys = pygame.key.get_pressed()

        forward = Vec3(math.sin(self.ball.yaw), 0.0, math.cos(self.ball.yaw))
        accel = 0.0

        if keys[pygame.K_UP]:
            accel += ACCELERATION
        if keys[pygame.K_DOWN]:
            accel -= BRAKE_ACCEL

        # 线性加速（只沿车头方向施加）
        self.ball.vel = self.ball.vel + forward * (accel * dt)

        turn_dir = 0.0
        if keys[pygame.K_LEFT]:
            turn_dir += 1.0
        if keys[pygame.K_RIGHT]:
            turn_dir -= 1.0

        speed_ratio = min(self.ball.vel.length() / MAX_SPEED, 1.0)
        self.ball.yaw += turn_dir * TURN_SPEED * (0.25 + 0.75 * speed_ratio) * dt

    def physics(self, dt: float):
        b = self.ball

        # 简单重力
        b.vel.y -= GRAVITY * dt

        # 限速
        speed = b.vel.length()
        if speed > MAX_SPEED:
            b.vel = b.vel * (MAX_SPEED / speed)

        b.pos = b.pos + b.vel * dt

        # 轨道边界碰撞（左右墙）
        if b.pos.x - BALL_RADIUS < -TRACK_HALF_WIDTH:
            b.pos.x = -TRACK_HALF_WIDTH + BALL_RADIUS
            if b.vel.x < 0.0:
                b.vel.x = -b.vel.x * RESTITUTION
        elif b.pos.x + BALL_RADIUS > TRACK_HALF_WIDTH:
            b.pos.x = TRACK_HALF_WIDTH - BALL_RADIUS
            if b.vel.x > 0.0:
                b.vel.x = -b.vel.x * RESTITUTION

        # 起点/终点边界
        if b.pos.z - BALL_RADIUS < 0.0:
            b.pos.z = BALL_RADIUS
            if b.vel.z < 0.0:
                b.vel.z = -b.vel.z * RESTITUTION
        elif b.pos.z + BALL_RADIUS > TRACK_LENGTH:
            b.pos.z = TRACK_LENGTH - BALL_RADIUS
            if b.vel.z > 0.0:
                b.vel.z = -b.vel.z * RESTITUTION

        # 地形碰撞（平地、斜坡、平台）
        ground = self.track.ground_height(b.pos.z)
        min_y = ground + BALL_RADIUS
        if b.pos.y < min_y:
            b.pos.y = min_y
            if b.vel.y < 0.0:
                b.vel.y = -b.vel.y * RESTITUTION

            # 接地摩擦
            b.vel.x *= FRICTION
            b.vel.z *= FRICTION

        # 轨道中间两个立方体障碍的碰撞（AABB vs Sphere）
        self.resolve_box_collision(center=Vec3(1.8, ground + 0.8, 36.0), half=Vec3(0.9, 0.8, 0.9))
        self.resolve_box_collision(center=Vec3(-1.5, ground + 0.8, 74.0), half=Vec3(1.2, 0.8, 1.0))

    def resolve_box_collision(self, center: Vec3, half: Vec3):
        b = self.ball
        cx = max(center.x - half.x, min(b.pos.x, center.x + half.x))
        cy = max(center.y - half.y, min(b.pos.y, center.y + half.y))
        cz = max(center.z - half.z, min(b.pos.z, center.z + half.z))

        closest = Vec3(cx, cy, cz)
        diff = b.pos - closest
        dist = diff.length()
        if dist < BALL_RADIUS:
            normal = diff.normalized() if dist > 1e-6 else Vec3(0.0, 1.0, 0.0)
            penetration = BALL_RADIUS - dist
            b.pos = b.pos + normal * penetration

            vn = b.vel.dot(normal)
            if vn < 0.0:
                b.vel = b.vel - normal * ((1.0 + RESTITUTION) * vn)

    def draw_track(self):
        # 主轨道
        glColor3f(0.18, 0.18, 0.18)
        strips = 120
        glBegin(GL_QUAD_STRIP)
        for i in range(strips + 1):
            z = TRACK_LENGTH * i / strips
            y = self.track.ground_height(z)
            glNormal3f(0.0, 1.0, 0.0)
            glVertex3f(-TRACK_HALF_WIDTH, y, z)
            glVertex3f(TRACK_HALF_WIDTH, y, z)
        glEnd()

        # 草地
        glColor3f(0.20, 0.50, 0.22)
        glBegin(GL_QUADS)
        glNormal3f(0.0, 1.0, 0.0)
        glVertex3f(-30, -0.01, -30)
        glVertex3f(30, -0.01, -30)
        glVertex3f(30, -0.01, 160)
        glVertex3f(-30, -0.01, 160)
        glEnd()

        # 边界护栏
        glColor3f(0.8, 0.15, 0.1)
        for x in (-TRACK_HALF_WIDTH, TRACK_HALF_WIDTH):
            glBegin(GL_LINE_STRIP)
            for i in range(strips + 1):
                z = TRACK_LENGTH * i / strips
                y = self.track.ground_height(z) + 0.6
                glVertex3f(x, y, z)
            glEnd()

    def draw_box(self, center: Vec3, half: Vec3):
        cx, cy, cz = center.x, center.y, center.z
        hx, hy, hz = half.x, half.y, half.z
        glPushMatrix()
        glTranslatef(cx, cy, cz)
        glScalef(hx * 2, hy * 2, hz * 2)
        glBegin(GL_QUADS)
        # top
        glNormal3f(0, 1, 0)
        glVertex3f(-0.5, 0.5, -0.5); glVertex3f(0.5, 0.5, -0.5); glVertex3f(0.5, 0.5, 0.5); glVertex3f(-0.5, 0.5, 0.5)
        # bottom
        glNormal3f(0, -1, 0)
        glVertex3f(-0.5, -0.5, -0.5); glVertex3f(-0.5, -0.5, 0.5); glVertex3f(0.5, -0.5, 0.5); glVertex3f(0.5, -0.5, -0.5)
        # front
        glNormal3f(0, 0, 1)
        glVertex3f(-0.5, -0.5, 0.5); glVertex3f(-0.5, 0.5, 0.5); glVertex3f(0.5, 0.5, 0.5); glVertex3f(0.5, -0.5, 0.5)
        # back
        glNormal3f(0, 0, -1)
        glVertex3f(-0.5, -0.5, -0.5); glVertex3f(0.5, -0.5, -0.5); glVertex3f(0.5, 0.5, -0.5); glVertex3f(-0.5, 0.5, -0.5)
        # left
        glNormal3f(-1, 0, 0)
        glVertex3f(-0.5, -0.5, -0.5); glVertex3f(-0.5, 0.5, -0.5); glVertex3f(-0.5, 0.5, 0.5); glVertex3f(-0.5, -0.5, 0.5)
        # right
        glNormal3f(1, 0, 0)
        glVertex3f(0.5, -0.5, -0.5); glVertex3f(0.5, -0.5, 0.5); glVertex3f(0.5, 0.5, 0.5); glVertex3f(0.5, 0.5, -0.5)
        glEnd()
        glPopMatrix()

    def draw_ball(self):
        b = self.ball
        glPushMatrix()
        glTranslatef(b.pos.x, b.pos.y, b.pos.z)
        glColor3f(0.9, 0.85, 0.2)
        quad = gluNewQuadric()
        gluSphere(quad, BALL_RADIUS, 24, 24)
        gluDeleteQuadric(quad)
        glPopMatrix()

    def set_camera(self):
        b = self.ball
        behind = Vec3(-math.sin(b.yaw), 0.36, -math.cos(b.yaw))
        eye = b.pos + behind * 11.5 + Vec3(0.0, 4.2, 0.0)
        target = b.pos + Vec3(math.sin(b.yaw), 0.5, math.cos(b.yaw)) * 5.0

        glLoadIdentity()
        gluLookAt(eye.x, eye.y, eye.z, target.x, target.y, target.z, 0.0, 1.0, 0.0)

    def render(self):
        glClearColor(0.55, 0.76, 0.95, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        self.set_camera()
        self.draw_track()

        glColor3f(0.2, 0.35, 0.9)
        self.draw_box(center=Vec3(1.8, self.track.ground_height(36.0) + 0.8, 36.0), half=Vec3(0.9, 0.8, 0.9))
        glColor3f(0.75, 0.3, 0.85)
        self.draw_box(center=Vec3(-1.5, self.track.ground_height(74.0) + 0.8, 74.0), half=Vec3(1.2, 0.8, 1.0))

        self.draw_ball()
        pygame.display.flip()

    def run(self):
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.03)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.running = False

            self.handle_input(dt)
            self.physics(dt)
            self.render()

        pygame.quit()


if __name__ == "__main__":
    try:
        Game().run()
    except Exception as e:
        print(f"运行失败: {e}")
        pygame.quit()
        sys.exit(1)
