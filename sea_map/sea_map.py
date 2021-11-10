from utilities import EARTH_CIRCUMFERENCE_VERTICAL, EARTH_CIRCUMFERENCE_HORIZONTAL, DEGREES_CIRCUMFERENCE, \
    Approximation, area_functions
from matplotlib.cm import get_cmap
from scipy.ndimage import label
import matplotlib.pyplot as plt
from file_read import readlast
from tqdm import tqdm
from glob import glob
import numpy as np
import click
import os


class Simulation:
    fp = ""
    num_lines = 0
    rise_m = 0.0
    approximations = []
    sea_levels = None
    data = {}
    spacing = ()
    results = {}

    def __init__(self, fp, mhs, mvs, rise_m, approx):
        self.map_file(fp)
        self.list_approximations(approx)
        self.find_spacing(mhs, mvs)
        self.set_sea_levels(rise_m)

    def map_file(self, fp):

        self.fp = os.path.abspath(os.path.join("../data/", fp))
        print(f"Mapping file: {self.fp}")

        data = dict()

        with open(self.fp, "r") as f:

            self.num_lines = len(f.readlines())

            # Grab the first and last line
            f.seek(0, 0)
            data["first"] = [float(i) for i in f.readline().split()]
            data["last"] = [float(i) for i in readlast(f, '\n').split()]

            # Find how many lines corresponds to one latitude jump
            f.seek(0, 0)
            first_lat = data["first"][0]

            counted_lines = 0
            curr_lat = first_lat
            while curr_lat == first_lat:
                counted_lines += 1
                curr_lat, curr_long, curr_elev = [float(i) for i in f.readline().split()]

            data["lines_per_lat"] = counted_lines - 1
            data["lines_per_lon"] = int(self.num_lines / data["lines_per_lat"])

        self.data = data

    def list_approximations(self, approx):
        if approx == Approximation.ALL:
            self.approximations = [approx for approx in Approximation if approx != Approximation.ALL]
        else:
            self.approximations = [approx]

    def find_spacing(self, mhs, mvs):

        first_lat, first_long = self.data["first"][:2]
        last_lat, last_long = self.data["last"][:2]

        if mhs == 0.0:
            lines_per_lon = self.data["lines_per_lon"]
            mhs = EARTH_CIRCUMFERENCE_HORIZONTAL / DEGREES_CIRCUMFERENCE * np.cos(np.deg2rad(first_lat)) \
                * abs(last_long - first_long) / lines_per_lon
        if mvs == 0.0:
            lines_per_lat = self.data["lines_per_lat"]
            mvs = EARTH_CIRCUMFERENCE_VERTICAL / DEGREES_CIRCUMFERENCE * abs(last_lat - first_lat) / lines_per_lat

        self.spacing = (mhs, mvs)

    def set_sea_levels(self, rise_m):

        self.rise_m = rise_m

        if rise_m == 0.0:
            self.sea_levels = np.linspace(1, 800, 50)
        else:
            self.sea_levels = np.array([self.rise_m])

    def find_area_above_water(self):

        num_sea_levels = len(self.sea_levels)
        results = {key: {
            "old_dry_area": np.zeros(num_sea_levels),
            "new_dry_area": np.zeros(num_sea_levels),
            "ratio": np.zeros(num_sea_levels),
            "a_old": np.zeros(self.num_lines),
            "a_new": np.zeros(self.num_lines)
        } for key in self.approximations}

        with open(self.fp, 'r') as f:
            for line_no, line in enumerate(tqdm(f, total=self.num_lines)):
                lat, lon, elev = [float(i) for i in line.split()]

                for approx in self.approximations:

                    # Find the area
                    area_func = area_functions[approx]
                    area = area_func(*self.spacing, lat, lon)

                    # Record the area as dry or not
                    for i, new_sea_level in enumerate(self.sea_levels):

                        if elev > 0.0:
                            results[approx]["old_dry_area"][i] += area
                            results[approx]["a_old"][line_no]       = 1
                        if elev > new_sea_level:
                            results[approx]["new_dry_area"][i]      += area
                            results[approx]["a_new"][line_no]       = 1

        for approx in self.approximations:
            for i, new_sea_level in enumerate(self.sea_levels):
                curr = results[approx]
                curr["ratio"][i] = curr["new_dry_area"][i] / curr["old_dry_area"][i]

        self.results = results

    def print_results_to_console(self):
        for approx in self.approximations:
            curr = self.results[approx]
            print(f"Results for approximation: {approx.name}")
            print(f"Old Dry Area: {curr['old_dry_area']} sq-km")
            print(f"New Dry Area: {curr['new_dry_area']} sq-km")
            print(f"Percentage remaining: {curr['ratio']}")

    def show_graph_of_sea_levels(self):

        fig, ax  = plt.subplots()
        for approx in self.approximations:
            ax.plot(self.sea_levels, self.results[approx]["ratio"] * 100, label=f"Approximation: {approx.name}")
        ax.legend()
        ax.set_xlabel("Sea level height increase [m]")
        ax.set_ylabel("Percentage of country still above water [%]")
        ax.set_title("Climate apocalypse")
        fig.show()
        # fig.savefig("../figs/sea_levels.png", dpi=300)

    def run(self):

        self.find_area_above_water()

        if self.rise_m > 0.0:
            self.print_results_to_console()
            self.print_map_count_islands()
        else:
            self.show_graph_of_sea_levels()

    def print_map_count_islands(self):

        q6 = click.prompt("Do you want to print a map of the area and the number of islands?",
                          type=click.Choice(["yes", "no"], case_sensitive=False),
                          default="yes")

        if q6 == "yes":
            self.show_map()

    def show_map(self):

        num_lat = self.data["lines_per_lat"]
        num_lon = self.data["lines_per_lon"]
        first   = self.data["first"]
        last    = self.data["last"]
        extent  = [first[1], last[1], last[0], first[0]]

        # reshapes the 1d array to a 2d array with length of unique longitudes and height of unique latitudes
        a_new = self.results[Approximation.FIRST]["a_new"]
        map_new = np.reshape(a_new, (num_lon, num_lat))

        a_old = self.results[Approximation.FIRST]["a_old"]
        map_old = np.reshape(a_old, (num_lon, num_lat))

        lbl, nlbls = label(map_new)
        print("The number of islands is:", nlbls)

        # plots the map
        fig, [ax0, ax1] = plt.subplots(1, 2)

        ax0.imshow(map_new, extent=extent, interpolation="none", origin="upper")
        ax0.set_title("Climate disaster down under")
        ax0.set_xlabel("Longitude [deg]")
        ax0.set_ylabel("Latitude [deg]")

        ax1.imshow(map_new - map_old, extent=extent, interpolation="none", origin="upper", cmap=get_cmap("RdGy"))
        ax1.set_title("Difference")
        ax1.set_xlabel("Longitude [deg]")
        ax1.set_ylabel("Latitude [deg]")

        fig.tight_layout()
        fig.show()
        # fig.savefig("../figs/sea_map.png", dpi=300)


def intro():
    """Welcomes the user and gathers relevant information."""

    greeting = click.prompt("Hello and welcome to this simulation program designed to simulate the effects of rising "
                            "sea levels. Are you excited?",
                            type=click.Choice(["yes", "no"], case_sensitive=False),
                            default="yes")

    if greeting == "yes":
        print("Great!")
    else:
        print("Oh well!")

    available_files = [os.path.basename(file) for file in sorted(glob("../data/*.txt"))]

    q1 = click.prompt("Please provide a filepath for a YXZ file to begin:",
                      type=click.Choice(available_files, case_sensitive=False),
                      default=available_files[0])

    q2 = click.prompt("Do you wish to provide the mean horizontal spacing (mhs)? If not, this will be calculated:",
                      type=float,
                      default=0.0)

    q3 = click.prompt("Do you wish to provide the mean vertical spacing (mvs)? If not, this will be calculated:",
                      type=float,
                      default=0.0)

    q4 = click.prompt("Do you wish to provide a specific sea level rise? If so, you will see how much land is currently"
                      " above sea level and you will have the opportunity to generate a map. If not, you will see a "
                      "graph showing how much land is still visible for various sea level increases.",
                      type=float,
                      default=0.0)

    q5_str = click.prompt("Do you wish to use the First or Second approximation of area? Or both?",
                          type=click.Choice(list(Approximation.__members__.keys()), case_sensitive=False),
                          default=Approximation.FIRST.name)

    q5 = getattr(Approximation, q5_str)

    return q1, q2, q3, q4, q5


def main():
    fp, mhs, mvs, rise_m, approx = intro()
    sim = Simulation(fp, mhs, mvs, rise_m, approx)
    sim.run()


if __name__ == "__main__":
    main()
