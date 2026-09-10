class SpatialTempo:
    def transform(self, obs, selected, controller):
        if (self.pathing or self.tempo) and self._continue_weed(
                obs, selected, controller, 24):
            return selected
        if not self.pathing and not self.tempo:
            return selected
        return self._suffix(obs, controller.R, 0, 24)
