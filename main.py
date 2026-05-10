import math
import sys
from dataclasses import dataclass

import pygame
from pygame.locals import DOUBLEBUF, OPENGL
from OpenGL.GL import *
from OpenGL.GLU import *

from map_data import OBSTACLES, ROAD_SEGMENTS, TRACK_LENGTH, ground_height, slope_dz

# ===== 全局参数 =====
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
FPS = 60

RESTITUTION = 0.55  # 弹性系数（碰撞反弹）
FRICTION = 0.985
GRAVITY = 30.0
GROUND_STICK_EPS = 0.05

BALL_RADIUS = 0.45
MAX_SPEED = 34.0
ACCELERATION = 22.0
BRAKE_ACCEL = 28.0
TURN_SPEED = 2.35  # rad/s

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
        return ground_height(z)

    def on_track(self, x: float, z: float) -> bool:
        if not (-40.0 <= x <= 40.0 and 0.0 <= z <= TRACK_LENGTH):
            return False
        for seg in ROAD_SEGMENTS:
            if self.point_to_segment_distance(x, z, seg.ax, seg.az, seg.bx, seg.bz) <= seg.half_width:
                return True
        return False

    @staticmethod
    def point_to_segment_distance(px, pz, ax, az, bx, bz):
        vx, vz = bx - ax, bz - az
        wx, wz = px - ax, pz - az
        c1 = vx * wx + vz * wz
        c2 = vx * vx + vz * vz
        t = 0.0 if c2 < 1e-8 else max(0.0, min(1.0, c1 / c2))
        cx, cz = ax + vx * t, az + vz * t
        return math.hypot(px - cx, pz - cz)

    def slope_dz(self, z: float) -> float:
        return slope_dz(z)

    def ground_normal(self, z: float) -> Vec3:
        # 高度场 y = h(z), 法线可写成 (0, 1, -h'(z))
        return Vec3(0.0, 1.0, -self.slope_dz(z)).normalized()


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

        # 赛道外回弹：找到最近道路中心线并拉回
        if not self.track.on_track(b.pos.x, b.pos.z):
            best = None
            best_d = 1e9
            for seg in ROAD_SEGMENTS:
                vx, vz = seg.bx - seg.ax, seg.bz - seg.az
                c2 = vx * vx + vz * vz
                if c2 < 1e-8:
                    continue
                t = max(0.0, min(1.0, ((b.pos.x - seg.ax) * vx + (b.pos.z - seg.az) * vz) / c2))
                cx, cz = seg.ax + vx * t, seg.az + vz * t
                dx, dz = b.pos.x - cx, b.pos.z - cz
                d = math.hypot(dx, dz)
                if d < best_d:
                    best_d = d
                    best = (seg, cx, cz, dx, dz)
            if best:
                seg, cx, cz, dx, dz = best
                nlen = math.hypot(dx, dz)
                nx, nz = (1.0, 0.0) if nlen < 1e-6 else (dx / nlen, dz / nlen)
                target_dist = seg.half_width - BALL_RADIUS
                b.pos.x = cx + nx * target_dist
                b.pos.z = cz + nz * target_dist
                vdot = b.vel.x * nx + b.vel.z * nz
                if vdot < 0.0:
                    b.vel.x -= (1.0 + RESTITUTION) * vdot * nx
                    b.vel.z -= (1.0 + RESTITUTION) * vdot * nz

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
        if b.pos.y <= min_y + GROUND_STICK_EPS:
            b.pos.y = min_y
            n = self.track.ground_normal(b.pos.z)
            vn = b.vel.dot(n)

            # 小幅度接地时，移除朝向地面的法向速度，避免“每帧下落-反弹”造成抖动
            if vn < 0.0:
                if abs(vn) < 1.2:
                    b.vel = b.vel - n * vn
                else:
                    b.vel = b.vel - n * ((1.0 + RESTITUTION) * vn)

            # 接地摩擦
            b.vel.x *= FRICTION
            b.vel.z *= FRICTION

        # 障碍物碰撞（AABB vs Sphere）
        for obs in OBSTACLES:
            center = Vec3(obs.x, self.track.ground_height(obs.z) + obs.y_offset, obs.z)
            half = Vec3(obs.hx, obs.hy, obs.hz)
            self.resolve_box_collision(center=center, half=half)

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
        # 多段道路（支持夹角道路）
        glColor3f(0.18, 0.18, 0.18)
        for seg in ROAD_SEGMENTS:
            vx, vz = seg.bx - seg.ax, seg.bz - seg.az
            ll = math.hypot(vx, vz)
            if ll < 1e-6:
                continue
            px, pz = -vz / ll, vx / ll
            ax1, az1 = seg.ax + px * seg.half_width, seg.az + pz * seg.half_width
            ax2, az2 = seg.ax - px * seg.half_width, seg.az - pz * seg.half_width
            bx1, bz1 = seg.bx + px * seg.half_width, seg.bz + pz * seg.half_width
            bx2, bz2 = seg.bx - px * seg.half_width, seg.bz - pz * seg.half_width
            glBegin(GL_QUADS)
            glNormal3f(0.0, 1.0, 0.0)
            glVertex3f(ax1, self.track.ground_height(az1), az1)
            glVertex3f(ax2, self.track.ground_height(az2), az2)
            glVertex3f(bx2, self.track.ground_height(bz2), bz2)
            glVertex3f(bx1, self.track.ground_height(bz1), bz1)
            glEnd()

        # 中线和分段标记
        glColor3f(0.92, 0.92, 0.92)
        glBegin(GL_QUADS)
        for i in range(16):
            z0 = 4.0 + i * 7.0
            z1 = z0 + 3.2
            y0 = self.track.ground_height(z0) + 0.01
            y1 = self.track.ground_height(z1) + 0.01
            glVertex3f(-0.15, y0, z0)
            glVertex3f(0.15, y0, z0)
            glVertex3f(0.15, y1, z1)
            glVertex3f(-0.15, y1, z1)
        glEnd()

        # 路侧减速带
        glColor3f(1.0, 0.95, 0.2)
        glBegin(GL_QUADS)
        for i in range(0, 22):
            z0 = 10.0 + i * 5.0
            z1 = z0 + 1.4
            y0 = self.track.ground_height(z0) + 0.01
            y1 = self.track.ground_height(z1) + 0.01
            for x in (-4.7, 4.3):
                glVertex3f(x, y0, z0)
                glVertex3f(x + 0.4, y0, z0)
                glVertex3f(x + 0.4, y1, z1)
                glVertex3f(x, y1, z1)
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
        for side in (-1.0, 1.0):
            glBegin(GL_LINE_STRIP)
            for i in range(strips + 1):
                z = TRACK_LENGTH * i / strips
                y = self.track.ground_height(z) + 0.6
                x = side * track_half_width(z)
                glVertex3f(x, y, z)
            glEnd()

        # 拱门（类似小隧道）
        glColor3f(0.35, 0.35, 0.38)
        for z in (22.0, 58.0, 96.0, 132.0, 176.0, 208.0):
            self.draw_arch(z)

    def draw_arch(self, z: float):
        y = self.track.ground_height(z)
        hw = track_half_width(z)
        self.draw_box(center=Vec3(-hw - 0.3, y + 1.4, z), half=Vec3(0.25, 1.4, 0.25))
        self.draw_box(center=Vec3(hw + 0.3, y + 1.4, z), half=Vec3(0.25, 1.4, 0.25))
        self.draw_box(center=Vec3(0.0, y + 2.75, z), half=Vec3(hw + 0.55, 0.25, 0.25))

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

        for obs in OBSTACLES:
            glColor3f(*obs.color)
            center = Vec3(obs.x, self.track.ground_height(obs.z) + obs.y_offset, obs.z)
            half = Vec3(obs.hx, obs.hy, obs.hz)
            self.draw_box(center=center, half=half)

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
