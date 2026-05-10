import math
import sys

import pygame
from OpenGL.GL import (
    GL_COLOR_BUFFER_BIT,
    GL_DEPTH_BUFFER_BIT,
    GL_DEPTH_TEST,
    GL_MODELVIEW,
    GL_PROJECTION,
    glClear,
    glClearColor,
    glEnable,
    glMatrixMode,
)
from OpenGL.GLU import gluLookAt, gluNewQuadric, gluPerspective, gluSphere

from terrain import Terrain, draw_terrain


def main() -> None:
    pygame.init()
    pygame.display.set_mode((1280, 720), pygame.DOUBLEBUF | pygame.OPENGL)
    pygame.display.set_caption("Eggy Racing")
    glEnable(GL_DEPTH_TEST)
    glClearColor(0.5, 0.72, 0.95, 1.0)
    glMatrixMode(GL_PROJECTION)
    gluPerspective(70, 1280 / 720, 0.1, 300)
    glMatrixMode(GL_MODELVIEW)

    from OpenGL.GL import glLoadIdentity, glPopMatrix, glPushMatrix, glTranslatef, glColor3f

    terrain = Terrain.load()
    ball = {"x": 0.0, "z": 0.0, "y": 2.0, "yaw": 0.0, "speed": 0.0}
    radius = 0.6
    accel = 6.0
    turn_rate = 95.0
    drag = 1.8
    clock = pygame.time.Clock()
    sphere = gluNewQuadric()

    while True:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit(0)

        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE]:
            pygame.quit()
            sys.exit(0)
        if keys[pygame.K_UP]:
            ball["speed"] += accel * dt
        if keys[pygame.K_DOWN]:
            ball["speed"] -= accel * dt
        if keys[pygame.K_LEFT]:
            ball["yaw"] += turn_rate * dt
        if keys[pygame.K_RIGHT]:
            ball["yaw"] -= turn_rate * dt

        ball["speed"] *= max(0.0, 1.0 - drag * dt)
        heading = math.radians(ball["yaw"])
        ball["x"] += math.sin(heading) * ball["speed"] * dt
        ball["z"] += math.cos(heading) * ball["speed"] * dt
        ground = terrain.sample_height(ball["x"], ball["z"])
        ball["y"] = ground + radius

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        cam_dist = 7.0
        cam_height = 3.0
        cx = ball["x"] - math.sin(heading) * cam_dist
        cz = ball["z"] - math.cos(heading) * cam_dist
        cy = ball["y"] + cam_height
        gluLookAt(cx, cy, cz, ball["x"], ball["y"], ball["z"], 0, 1, 0)

        draw_terrain(terrain)
        glPushMatrix()
        glTranslatef(ball["x"], ball["y"], ball["z"])
        glColor3f(0.95, 0.85, 0.35)
        gluSphere(sphere, radius, 20, 20)
        glPopMatrix()

        pygame.display.set_caption(f"Eggy Racing speed={ball['speed']:.2f}")
        pygame.display.flip()


if __name__ == "__main__":
    main()
