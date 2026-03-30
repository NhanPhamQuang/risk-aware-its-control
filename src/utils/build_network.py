import os

def build():
    os.system(
        "netconvert --osm-files data/map.osm -o network/map.net.xml "
        "--tls.guess true --junctions.join true"
    )

if __name__ == "__main__":
    build()