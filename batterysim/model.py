"""
This module contains a simple battery model.

"""
import json
import arrow

DATE_FORMAT = 'YYYY-MM-DD HH:mm'
"""Date format used to convert strings to dates."""


class Battery:
    """
    Simple model for one battery
    """
    def __init__(self, init_charge=0, capacity=10, round_trip_eff=0.87, resolution=1):
        self.charge = init_charge
        self.capacity = capacity
        self.round_trip_eff = round_trip_eff
        self.resolution = resolution
        self.power_rating = 0

    def step(self):
        next_charge = self.charge + self.resolution * self.round_trip_eff * self.power_rating
        if next_charge <= self.capacity :
            self.charge = next_charge


def eid(i):
    return 'battery_%d' % i


class BatteryModel:
    def __init__(self, data, name_grid):
        # Process meta data
        assert next(data).startswith('# meta')
        meta = json.loads(next(data))
        self.start = arrow.get(meta['start_date'], DATE_FORMAT)
        self.unit = meta['unit']
        self.num_batteries = meta['num_batteries']
        self.resolution = meta['resolution']

        # Obtain id lists
        assert next(data).startswith('# id_list')
        id_list = json.loads(next(data))
        self.node_ids = id_list[name_grid]

        """List of power grid node IDs for which to create batteries."""

        assert next(data).startswith('# attrs')
        attr_list = json.loads(next(data))

        #: List of batteries info dicts
        self.batteries = [{
            'object':
            Battery(
                init_charge=attr_list['init_charge'][i],
                capacity=attr_list['capacity'][i],
                round_trip_eff=attr_list['round_trip_eff'][i],
                resolution=self.resolution,
            ),
            'num':
            i + 1,
            'node_id':
            n,
        } for i, n in enumerate(self.node_ids)]

        self.batteries_by_eid = {
                eid(i): battery['object']
                for i, battery in enumerate(self.batteries)
        }

        # Helpers for get()
        self._last_date = None
        self._cache = None

    def step(self, deltas=None):
        """Set new model inputs from *deltas* to the models and perform a
        simulation step.
        *deltas* is a dictionary that maps model indices to new delta values
        for the model.
        """
        if deltas:
            for eid, delta in deltas.items():
                self.batteries_by_eid[eid].delta = delta

        for battery in self.batteries:
            battery['object'].step()

    def get(self, minutes):
        """Get the current load for all batteries for *minutes* minutes since
        :attr:`start`.
        """

        # TODO: delta should be an order of the rate and the battery start to charge or discharge at this rate, then when we call get, it should count the time spent and charge or discharge the battery of that much since the order.
        # For now we just return the value of soc.

        self._cache = [
                battery['object'].charge
                for i, battery in enumerate(self.batteries)
                    ]
        return self._cache

    def get_delta(self, date):
        """Get the amount of minutes between *date* and :attr:`start`.
        The date needs to be a strings formated like :data:`DATE_FORMAT`.
        Raise a :exc:`ValueError` if *date* is smaller than :attr:`start`.
        """
        date = arrow.get(date, DATE_FORMAT)
        if date < self.start:
            raise ValueError(
                'date must >= "%s".' % self.start.format(DATE_FORMAT))
        dt = date - self.start
        minutes = (dt.days * 1440) + (dt.seconds // 60)
        return minutes
