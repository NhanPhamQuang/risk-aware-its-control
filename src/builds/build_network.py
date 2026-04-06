import os

def build():
    os.system(
        "netconvert "
        "--osm-files data/map2.osm "
        "-o network/map.net.xml "
        "--geometry.remove "
        "--ramps.guess "
        "--junctions.join "
        "--tls.guess-signals "
        "--tls.discard-simple "
        "--tls.join "
        "--no-turnarounds true "
        "--remove-edges.by-type highway.service,highway.residential,highway.footway,highway.path "
        "--keep-edges.by-vclass passenger "
    )

if __name__ == "__main__":
    build()