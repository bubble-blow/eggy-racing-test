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
from OpenGL.GLU import gluPerspective

from terrain import Terrain, draw_terrain


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((1200, 720), pygame.DOUBLEBUF | pygame.OPENGL)
    pygame.display.set_caption("Terrain Editor")
    glEnable(GL_DEPTH_TEST)
    glClearColor(0.08, 0.1, 0.16, 1.0)
    glMatrixMode(GL_PROJECTION)
    gluPerspective(60, 1200 / 720, 0.1, 200)
    glMatrixMode(GL_MODELVIEW)

    from OpenGL.GL import GL_LINE_LOOP, glBegin, glColor3f, glEnd, glLoadIdentity, glRotatef, glTranslatef, glVertex3f

    terrain = Terrain.load()
    mode = "fixed"
    brush_height = 2.0
    cursor = [terrain.width // 2, terrain.height // 2]



    def draw_cursor_highlight() -> None:
        x, y = cursor
        wx = x - terrain.width / 2
        wz = y - terrain.height / 2
        h00 = terrain.heights[y, x]
        x1 = min(x + 1, terrain.width - 1)
        y1 = min(y + 1, terrain.height - 1)
        h10 = terrain.heights[y, x1]
        h11 = terrain.heights[y1, x1]
        h01 = terrain.heights[y1, x]
        offset = 0.06
        glColor3f(1.0, 0.2, 0.2)
        glBegin(GL_LINE_LOOP)
        glVertex3f(wx, h00 + offset, wz)
        glVertex3f(wx + 1, h10 + offset, wz)
        glVertex3f(wx + 1, h11 + offset, wz + 1)
        glVertex3f(wx, h01 + offset, wz + 1)
        glEnd()

    clock = pygame.time.Clock()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                terrain.save()
                pygame.quit()
                sys.exit(0)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    terrain.save()
                    pygame.quit()
                    sys.exit(0)
                if event.key == pygame.K_TAB:
                    mode = "adaptive" if mode == "fixed" else "fixed"
                if event.key == pygame.K_s:
                    terrain.save()
                if event.key == pygame.K_EQUALS:
                    brush_height += 0.5
                if event.key == pygame.K_MINUS:
                    brush_height -= 0.5
                if event.key == pygame.K_SPACE:
                    terrain.set_height(cursor[0], cursor[1], brush_height, mode)

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            cursor[0] = max(0, cursor[0] - 1)
        if keys[pygame.K_RIGHT]:
            cursor[0] = min(terrain.width - 1, cursor[0] + 1)
        if keys[pygame.K_UP]:
            cursor[1] = max(0, cursor[1] - 1)
        if keys[pygame.K_DOWN]:
            cursor[1] = min(terrain.height - 1, cursor[1] + 1)

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        glTranslatef(0.0, -4.5, -32)
        glRotatef(35, 1, 0, 0)
        draw_terrain(terrain, wireframe=True)
        draw_cursor_highlight()
        pygame.display.flip()
        pygame.display.set_caption(f"Editor mode={mode} brush={brush_height:.1f} cursor={tuple(cursor)}")
        clock.tick(15)


if __name__ == "__main__":
    main()
