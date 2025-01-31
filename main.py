import sys
import pygame
from settings import Settings
from ship import Ship
from bullet import Bullet
from alien import Alien
from time import sleep
from game_stats import GameStats
from button import Button
from scoreboard import ScoreBoard


class AlienInvasion:
    """overall class to manage game assets and behaviour."""
    def __init__(self) -> None:
        """Initialize the game and create game resources."""
        pygame.init()
        self.clock = pygame.time.Clock()

        self.settings = Settings()

        self.screen = pygame.display.set_mode((self.settings.screen_width, self.settings.screen_height))
        pygame.display.set_caption("Alien Invasion")

        # instance to use game statistics and create a scoreboard
        self.stats = GameStats(self)
        self.sb = ScoreBoard(self)

        self.ship = Ship(self)
        self.bullets = pygame.sprite.Group()
        self.aliens = pygame.sprite.Group()

        self._create_fleet()

        # start alien invasion in an active state.
        self.game_active = False
        self.paused = False

        # make the play button
        self.play_button = Button(self, "Play")

    def run_game(self):
        "start the main loop of the game."
        while True:
            self._check_events()
            if self.game_active and not self.paused:
                self.ship.update()
                self._update_bullets()
                self._update_aliens()
            self._update_screen()
            self.clock.tick(60)

    
    def _check_events(self):
        # watches for keyboard and mouse events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                self._check_keydown_events(event)
            elif event.type == pygame.KEYUP:
                self._check_keyup_events(event)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                self._check_play_button(mouse_pos)
    
    def _check_play_button(self, mouse_pos):
        """start a new game when the player clicks play."""
        button_clicked = self.play_button.rect.collidepoint(mouse_pos)
        if button_clicked and not self.game_active:
            # reset the game settings.
            self.settings.initialize_dynamic_settings()
            
            self._p_for_play()

    def _p_for_play(self):
         # reset the game statistics.
        self.stats.reset_stats()
        self.sb.prep_score()
        self.sb.prep_level()
        self.sb.prep_ships()
        self.game_active = True
        self.paused = False
        # get rid of any remaining bullets and aliens.
        self.bullets.empty()
        self.aliens.empty()
        # create a new fleet and center the ship.
        self._create_fleet()
        self.ship.center_ship()
        # hide the mouse cursor
        pygame.mouse.set_visible(False)


            
    def _check_keydown_events(self, event):
        if event.key == pygame.K_RIGHT:
            self.ship.moving_right = True
        if event.key == pygame.K_LEFT:
            self.ship.moving_left = True
        elif event.key == pygame.K_q:
            sys.exit()
        elif event.key == pygame.K_SPACE:
            self._fire_bullet()
        elif event.key == pygame.K_s and not self.game_active:
            self._p_for_play()
        elif event.key == pygame.K_p:
            if self.game_active:
                self._pause_game()

    def _pause_game(self):
        """pause the game."""
        self.paused = True
        font = pygame.font.SysFont(None, 48)
        pause_text = font.render("Paused. Press 'R' to resume.", True, (255, 255, 255))
        clock = pygame.time.Clock()

        while self.paused:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        self.paused = False
                    if event.key == pygame.K_q:
                        sys.exit()
            self.screen.fill((0, 0, 0))
            self.screen.blit(pause_text, (100, 250))
            pygame.display.update()

            clock.tick(10)

    def _check_keyup_events(self, event):
        if event.key == pygame.K_RIGHT:
            self.ship.moving_right = False
        elif event.type == pygame.KEYUP:
            self.ship.moving_left = False
 
    
    def _ship_hit(self):
        """respond to ship being hit by an alien."""
        # decrement ships to the left
        if self.stats.ships_left > 0:
            self.stats.ships_left -= 1
            self.sb.prep_ships()

            # get rid of any remaining bullets and aliens.
            self.bullets.empty()
            self.aliens.empty()

            # create a new fleet and center the ship.
            self._create_fleet()
            self.ship.center_ship()

            # pause
            sleep(0.5)
        else:
            self.game_active = False
            pygame.mouse.set_visible(True)

    def _check_aliens_bottom(self):
        """check if any alien has reached the bottom of the screen."""
        for alien in self.aliens.sprites():
            if alien.rect.bottom >= self.settings.screen_height:
                # treat this the same like the ship got hit
                self._ship_hit()
                break

    
    def _fire_bullet(self):
        """create a bullet and add it to the bullets group."""
        if len(self.bullets) < self.settings.bullets_allowed:
            new_bullet = Bullet(self)
            self.bullets.add(new_bullet)

    def _update_bullets(self):
        """update the position of bullets and gets rid of old bullets."""
        # update bullet positions
        self.bullets.update()

        # get rid of old bullets that have crossed the screen.
        for bullet in self.bullets.copy():
            if bullet.rect.bottom <=0:
                self.bullets.remove(bullet)

        self._check_bullet_alien_collisions()
    
    def _check_bullet_alien_collisions(self):
        """respond to bullet alien collisions."""
        # remove any bullet or aliens that may have collided.
        collisions = pygame.sprite.groupcollide(self.bullets, self.aliens, True, True)

        if collisions:
            for aliens in collisions.values():
                self.stats.score += self.settings.alien_points
            self.sb.prep_score()
            self.sb.check_high_score()

        if not self.aliens:
            # destroy existing bullets and create a new fleet.
            self.bullets.empty()
            self._create_fleet()
            self.settings.increase_speed()

            # increase level
            self.stats.level +=1
            self.sb.prep_level()
    
    def _update_aliens(self):
        """Update the positions of all aliens in the fleet."""
        self._check_fleet_edges()
        self.aliens.update()

        # look for alien-ship collisions.
        if pygame.sprite.spritecollideany(self.ship, self.aliens):
            self._ship_hit()
        
        # look for aliens hitting the bottom of the screen.
        self._check_aliens_bottom()

    def _create_fleet(self):
        """Create the fleet of aliens."""
        # create an alien and keep adding aliens until there is no room left.
        # spacing between aliens is one alien width.
        alien = Alien(self)
        alien_width, alien_height = alien.rect.size

        current_x, current_y = alien_width, alien_height
        while (current_y < (self.settings.screen_height - 3 * alien_height)):
            while (current_x < (self.settings.screen_width - 2 * alien_width)):
                self._create_alien(current_x, current_y)
                current_x += 2 * alien_width

            current_x = alien_width
            current_y += 2 * alien_height

    def _create_alien(self, x_position, y_position):
        """Create an alien and place it in this row."""
        new_alien = Alien(self)
        new_alien.x = x_position
        new_alien.rect.x = x_position
        new_alien.rect.y = y_position
        self.aliens.add(new_alien)
    
    def _check_fleet_edges(self):
        """Respond appropriately if any aliens have reached an edge."""
        for alien in self.aliens.sprites():
            if alien.check_edges():
                self._change_fleet_direction()
                break
    
    def _change_fleet_direction(self):
        """drop the entire fleet and change the fleet's direction."""
        for alien in self.aliens.sprites():
            alien.rect.y += self.settings.fleet_drop_speed
        self.settings.fleet_direction *= -1

    def _update_screen(self):
        # update the images on the screen and flip to the new screen.
        self.screen.fill(self.settings.bgcolor)
        for bullet in self.bullets.sprites():
            bullet.draw_bullet()
        self.ship.blitme()
        self.aliens.draw(self.screen)

        # draw the score information
        self.sb.show_score()


        # draw the play button if the game is inactive.
        if not self.game_active:
            self.play_button.draw_button()

        # make the most recently drawn screen visible
        pygame.display.flip()

        

ai = AlienInvasion()
ai.run_game()
