"""
星表数据初始化脚本
生成包含真实天文数据的离线星表数据库
"""

import sqlite3
import os
from pathlib import Path

DATA_DIR = Path(__file__).parent / 'data'
DB_PATH = DATA_DIR / 'star_catalogs.db'
CATALOG_DIR = DATA_DIR / 'star_catalogs'

BRIGHT_STARS = [
    (1, "Sirius", 101.287, -16.716, -1.46, "A1V", "CMa"),
    (2, "Canopus", 95.988, -52.696, -0.72, "F0Ib", "Car"),
    (3, "Arcturus", 213.915, 19.182, -0.05, "K1.5III", "Boo"),
    (4, "Alpha Centauri A", 219.901, -60.834, -0.01, "G2V", "Cen"),
    (5, "Vega", 279.235, 38.784, 0.03, "A0V", "Lyr"),
    (6, "Capella", 79.172, 45.998, 0.08, "G8III", "Aur"),
    (7, "Rigel", 78.635, -8.202, 0.18, "B8Ia", "Ori"),
    (8, "Procyon", 114.826, 5.225, 0.40, "F5IV-V", "CMi"),
    (9, "Achernar", 24.429, -57.237, 0.45, "B3Vpe", "Eri"),
    (10, "Betelgeuse", 88.793, 7.407, 0.50, "M2Iab", "Ori"),
    (11, "Hadar", 210.956, -60.373, 0.61, "B1III", "Cen"),
    (12, "Altair", 297.696, 8.868, 0.76, "A7V", "Aql"),
    (13, "Acrux", 186.650, -63.099, 0.77, "B0.5IV", "Cru"),
    (14, "Aldebaran", 68.980, 16.509, 0.87, "K5III", "Tau"),
    (15, "Antares", 247.352, -26.432, 1.06, "M1.5Iab", "Sco"),
    (16, "Spica", 201.298, -11.161, 0.98, "B1V", "Vir"),
    (17, "Pollux", 116.329, 28.026, 1.16, "K0III", "Gem"),
    (18, "Fomalhaut", 344.413, -29.622, 1.17, "A3V", "PsA"),
    (19, "Deneb", 310.358, 45.280, 1.25, "A2Ia", "Cyg"),
    (20, "Mimosa", 191.930, -59.689, 1.25, "B0.5III", "Cru"),
    (21, "Regulus", 152.093, 11.967, 1.36, "B7V", "Leo"),
    (22, "Adhara", 104.656, -28.972, 1.50, "B2II", "CMa"),
    (23, "Castor", 113.649, 31.888, 1.58, "A1V", "Gem"),
    (24, "Shaula", 263.402, -37.104, 1.62, "B1.5IV", "Sco"),
    (25, "Bellatrix", 81.283, 6.350, 1.64, "B2III", "Ori"),
    (26, "Elnath", 81.573, 28.607, 1.65, "B7III", "Tau"),
    (27, "Miaplacidus", 138.300, -69.717, 1.67, "A2IV", "Car"),
    (28, "Alnilam", 84.053, -1.202, 1.69, "B0Ia", "Ori"),
    (29, "Alnitak", 85.190, -1.943, 1.74, "O9.5Ib", "Ori"),
    (30, "Alioth", 193.507, 55.960, 1.76, "A0pCr", "UMa"),
    (31, "Dubhe", 165.932, 61.751, 1.81, "K0III", "UMa"),
    (32, "Mirfak", 51.081, 49.861, 1.79, "F5Ib", "Per"),
    (33, "Wezen", 107.098, -26.393, 1.83, "F8Ia", "CMa"),
    (34, "Sargas", 264.330, -42.998, 1.86, "F1II", "Sco"),
    (35, "Kaus Australis", 276.043, -34.385, 1.85, "B9.5III", "Sgr"),
    (36, "Avior", 125.629, -59.509, 1.86, "K3III", "Car"),
    (37, "Alkaid", 206.885, 49.313, 1.85, "B3V", "UMa"),
    (38, "Menkalinan", 89.882, 44.947, 1.90, "A2V", "Aur"),
    (39, "Atria", 253.084, -69.028, 1.91, "K2IIb", "TrA"),
    (40, "Alhena", 99.428, 16.399, 1.93, "A0IV", "Gem"),
    (41, "Peacock", 306.412, -56.735, 1.94, "B2IV", "Pav"),
    (42, "Polaris", 37.955, 89.264, 1.97, "F7Ib", "UMi"),
    (43, "Mirzam", 95.675, -17.956, 1.98, "B1II-III", "CMa"),
    (44, "Alphard", 141.897, -8.659, 1.99, "K3II-III", "Hya"),
    (45, "Hamal", 31.793, 23.462, 2.01, "K2III", "Ari"),
    (46, "Diphda", 10.897, -17.987, 2.04, "K0III", "Cet"),
    (47, "Mizar", 200.981, 54.925, 2.23, "A1V", "UMa"),
    (48, "Nunki", 283.816, -26.297, 2.05, "B2.5V", "Sgr"),
    (49, "Menkent", 219.570, -36.371, 2.06, "K0III", "Cen"),
    (50, "Alpheratz", 2.097, 29.090, 2.07, "B9p", "And"),
    (51, "Rasalhague", 263.054, 12.560, 2.08, "A5III", "Oph"),
    (52, "Kochab", 222.676, 74.156, 2.07, "K4III", "UMi"),
    (53, "Saiph", 86.939, -9.670, 2.07, "B0.5Ia", "Ori"),
    (54, "Denebola", 177.265, 14.572, 2.14, "A3V", "Leo"),
    (55, "Algieba", 154.993, 19.841, 2.01, "K0III", "Leo"),
    (56, "Enif", 326.046, 9.875, 2.38, "K2Ib", "Peg"),
    (57, "Scheat", 345.944, 28.083, 2.44, "M2.5II-III", "Peg"),
    (58, "Markab", 346.190, 15.206, 2.49, "B9III", "Peg"),
    (59, "Algenib", 3.309, 15.184, 2.84, "B2IV", "Peg"),
    (60, "Mirach", 17.433, 35.621, 2.07, "M0III", "And"),
    (61, "Almach", 30.975, 42.330, 2.10, "K3III", "And"),
    (62, "Schedar", 10.127, 56.537, 2.24, "K0IIIa", "Cas"),
    (63, "Caph", 2.294, 59.150, 2.28, "F2III-IV", "Cas"),
    (64, "Ruchbah", 16.400, 60.717, 2.66, "A5V", "Cas"),
    (65, "Segin", 23.941, 63.670, 3.38, "B3III", "Cas"),
    (66, "Algol", 47.042, 40.956, 2.09, "B8V", "Per"),
    (67, "Menkar", 45.570, 4.090, 2.54, "M2III", "Cet"),
    (68, "Baten Kaitos", 29.281, -10.335, 3.74, "K0III", "Cet"),
    (69, "Mira", 34.837, -2.977, 3.04, "M7IIIe", "Cet"),
    (70, "Rigil Kentaurus", 219.901, -60.834, -0.27, "G2V+K1V", "Cen"),
    (71, "Proxima Centauri", 217.429, -62.679, 11.05, "M5.5Ve", "Cen"),
    (72, "Barnard's Star", 269.454, 4.693, 9.53, "M4.0V", "Oph"),
    (73, "Wolf 359", 164.120, 7.015, 13.44, "M6.0V", "Leo"),
    (74, "Lalande 21185", 165.834, 35.970, 7.47, "M2.0V", "UMa"),
    (75, "Sirius B", 101.289, -16.716, 8.44, "DA2", "CMa"),
    (76, "Epsilon Eridani", 53.233, -9.458, 3.73, "K2V", "Eri"),
    (77, "61 Cygni A", 316.213, 38.749, 5.21, "K5V", "Cyg"),
    (78, "Tau Ceti", 26.017, -15.939, 3.49, "G8.5V", "Cet"),
    (79, "Luyten's Star", 111.854, 5.226, 9.85, "M3.5V", "CMi"),
    (80, "Teegarden's Star", 43.254, 16.881, 15.14, "M7.0V", "Ari"),
    (81, "TRAPPIST-1", 346.622, -5.041, 18.80, "M8V", "Aqr"),
    (82, "Ross 128", 176.935, 0.804, 11.13, "M4V", "Vir"),
    (83, "Gliese 581", 229.860, -7.722, 10.55, "M3V", "Lib"),
    (84, "Kepler-22", 289.217, 47.884, 11.66, "G5V", "Cyg"),
    (85, "HD 209458", 330.795, 18.884, 7.65, "G0V", "Peg"),
    (86, "51 Pegasi", 344.366, 20.769, 5.49, "G2IV", "Peg"),
    (87, "Kapteyn's Star", 77.919, -45.018, 8.85, "M1.5V", "Pic"),
    (88, "Groombridge 34", 4.592, 44.022, 8.08, "M1.5V", "And"),
    (89, "Lacaille 9352", 346.494, -35.853, 7.34, "M0.5V", "PsA"),
    (90, "Gliese 876", 343.320, -14.256, 10.17, "M4V", "Aqr"),
    (91, "Gliese 667 C", 259.745, -34.997, 10.22, "M1.5V", "Sco"),
    (92, "Kepler-186", 298.653, 43.955, 15.29, "M1V", "Cyg"),
    (93, "Kepler-452", 295.013, 44.277, 13.43, "G2V", "Cyg"),
    (94, "TOI-700", 97.096, -65.578, 13.10, "M2V", "Dor"),
    (95, "Gliese 1132", 153.596, -47.157, 13.46, "M4V", "Vel"),
    (96, "LHS 1140", 11.214, -15.274, 14.15, "M4.5V", "Cet"),
    (97, "Gliese 1214", 258.830, 4.960, 14.67, "M4.5V", "Oph"),
    (98, "HD 40307", 84.521, -60.024, 7.17, "K2.5V", "Pic"),
    (99, "Kepler-62", 283.213, 45.348, 13.75, "K2V", "Lyr"),
    (100, "Kepler-442", 285.367, 39.282, 15.30, "K5V", "Lyr"),
]

NGC_IC_OBJECTS = [
    ("NGC224", 10.684, 41.269, 3.44, 190.5, "galaxy", "And"),
    ("NGC1976", 83.822, -5.391, 4.00, 65.0, "nebula", "Ori"),
    ("NGC1952", 83.633, 22.015, 8.40, 6.0, "nebula", "Tau"),
    ("NGC5194", 202.470, 47.195, 8.40, 11.2, "galaxy", "CVn"),
    ("NGC6205", 250.424, 36.461, 5.80, 20.0, "globular_cluster", "Her"),
    ("NGC3031", 148.888, 69.065, 6.94, 26.9, "galaxy", "UMa"),
    ("NGC5457", 210.802, 54.349, 7.86, 28.8, "galaxy", "UMa"),
    ("NGC4594", 189.998, -11.623, 8.00, 8.7, "galaxy", "Vir"),
    ("NGC6720", 283.396, 33.029, 8.80, 1.4, "planetary_nebula", "Lyr"),
    ("NGC6523", 270.921, -24.387, 6.00, 45.0, "nebula", "Sgr"),
    ("NGC1432", 56.871, 24.105, 1.60, 110.0, "open_cluster", "Tau"),
    ("NGC5139", 201.298, -47.480, 3.90, 36.3, "globular_cluster", "Cen"),
    ("NGC7000", 314.675, 44.363, 4.00, 120.0, "nebula", "Cyg"),
    ("NGC2237", 97.980, 4.940, 4.80, 80.0, "nebula", "Mon"),
    ("NGC6960", 311.400, 30.710, 7.00, 70.0, "nebula", "Cyg"),
    ("NGC6992", 314.150, 31.720, 7.00, 60.0, "nebula", "Cyg"),
    ("NGC6611", 274.700, -13.807, 6.00, 7.0, "open_cluster", "Ser"),
    ("NGC6853", 299.902, 22.721, 7.50, 8.0, "planetary_nebula", "Vul"),
    ("NGC2264", 100.242, 9.896, 4.10, 20.0, "open_cluster", "Mon"),
    ("NGC3372", 161.265, -59.867, 1.00, 120.0, "nebula", "Car"),
    ("NGC4486", 187.706, 12.391, 8.63, 8.3, "galaxy", "Vir"),
    ("NGC4303", 185.479, 4.474, 9.65, 6.5, "galaxy", "Vir"),
    ("NGC4254", 184.707, 14.417, 9.89, 5.4, "galaxy", "Com"),
    ("NGC4321", 185.729, 15.822, 9.35, 7.4, "galaxy", "Com"),
    ("NGC3351", 160.991, 11.704, 9.73, 7.4, "galaxy", "Leo"),
    ("NGC3623", 169.733, 13.087, 9.29, 8.7, "galaxy", "Leo"),
    ("NGC3627", 170.062, 12.991, 8.92, 9.1, "galaxy", "Leo"),
    ("NGC4569", 189.208, 13.163, 9.54, 9.5, "galaxy", "Vir"),
    ("NGC4579", 189.431, 11.818, 9.93, 5.9, "galaxy", "Vir"),
    ("NGC4501", 188.000, 14.420, 9.39, 6.9, "galaxy", "Com"),
    ("NGC4388", 186.445, 12.662, 11.02, 5.6, "galaxy", "Vir"),
    ("NGC4402", 186.532, 13.115, 11.30, 3.9, "galaxy", "Vir"),
    ("NGC4438", 186.940, 13.009, 10.17, 8.5, "galaxy", "Vir"),
    ("NGC4192", 183.451, 14.898, 10.07, 9.8, "galaxy", "Com"),
    ("NGC4216", 183.975, 13.149, 10.01, 8.3, "galaxy", "Vir"),
    ("NGC4535", 188.585, 8.198, 9.82, 7.1, "galaxy", "Vir"),
    ("NGC4548", 188.860, 14.496, 10.23, 5.4, "galaxy", "Com"),
    ("NGC4567", 189.136, 11.258, 11.31, 3.1, "galaxy", "Vir"),
    ("NGC4568", 189.143, 11.237, 10.90, 4.6, "galaxy", "Vir"),
    ("NGC4571", 189.225, 14.220, 11.20, 3.6, "galaxy", "Com"),
    ("NGC4651", 190.930, 16.394, 10.78, 4.0, "galaxy", "Com"),
    ("NGC4654", 190.986, 13.126, 10.46, 5.0, "galaxy", "Vir"),
    ("NGC4689", 191.940, 13.762, 10.88, 4.3, "galaxy", "Com"),
    ("NGC4698", 192.095, 8.487, 10.66, 4.0, "galaxy", "Vir"),
    ("NGC4710", 192.412, 15.165, 11.00, 4.9, "galaxy", "Com"),
    ("NGC4754", 193.073, 11.314, 10.55, 4.6, "galaxy", "Vir"),
    ("NGC4762", 193.233, 11.229, 10.22, 8.7, "galaxy", "Vir"),
    ("NGC4826", 194.182, 21.683, 8.52, 10.0, "galaxy", "Com"),
    ("NGC5055", 198.955, 42.029, 8.52, 12.6, "galaxy", "CVn"),
    ("NGC5236", 204.254, -29.865, 7.54, 12.9, "galaxy", "Hya"),
    ("NGC5272", 205.548, 28.377, 6.20, 18.0, "globular_cluster", "CVn"),
    ("NGC5866", 226.623, 55.763, 9.89, 4.7, "galaxy", "Dra"),
    ("NGC5904", 229.638, 2.081, 5.65, 23.0, "globular_cluster", "Ser"),
    ("NGC5986", 233.107, -37.786, 7.52, 9.8, "globular_cluster", "Lup"),
    ("NGC6093", 244.260, -22.976, 7.33, 8.9, "globular_cluster", "Sco"),
    ("NGC6121", 245.897, -26.526, 5.60, 36.0, "globular_cluster", "Sco"),
    ("NGC6171", 248.133, -13.054, 7.93, 10.0, "globular_cluster", "Oph"),
    ("NGC6218", 251.809, -1.949, 6.70, 16.0, "globular_cluster", "Oph"),
    ("NGC6254", 254.288, -4.099, 6.60, 20.0, "globular_cluster", "Oph"),
    ("NGC6266", 255.302, -30.114, 6.45, 14.0, "globular_cluster", "Sco"),
    ("NGC6273", 255.657, -26.268, 6.80, 16.0, "globular_cluster", "Oph"),
    ("NGC6333", 259.798, -18.516, 7.72, 12.0, "globular_cluster", "Oph"),
    ("NGC6341", 259.281, 43.136, 6.44, 14.0, "globular_cluster", "Her"),
    ("NGC6356", 260.896, -17.813, 8.25, 10.0, "globular_cluster", "Oph"),
    ("NGC6397", 265.175, -53.674, 5.73, 32.0, "globular_cluster", "Ara"),
    ("NGC6402", 264.401, -3.246, 7.59, 11.7, "globular_cluster", "Oph"),
    ("NGC6541", 272.010, -43.714, 6.30, 15.0, "globular_cluster", "CrA"),
    ("NGC6626", 276.137, -24.870, 6.79, 14.0, "globular_cluster", "Sgr"),
    ("NGC6637", 277.849, -32.348, 7.64, 8.4, "globular_cluster", "Sgr"),
    ("NGC6656", 279.100, -23.905, 5.10, 32.0, "globular_cluster", "Sgr"),
    ("NGC6681", 283.540, -32.292, 7.87, 8.0, "globular_cluster", "Sgr"),
    ("NGC6715", 283.764, -30.480, 7.60, 12.0, "globular_cluster", "Sgr"),
    ("NGC6752", 287.717, -59.985, 5.40, 29.0, "globular_cluster", "Pav"),
    ("NGC6779", 289.148, 30.183, 8.37, 8.3, "globular_cluster", "Lyr"),
    ("NGC6809", 295.000, -30.965, 6.32, 19.0, "globular_cluster", "Sgr"),
    ("NGC6838", 298.444, 18.779, 8.19, 7.2, "globular_cluster", "Sge"),
    ("NGC6864", 301.520, -21.921, 8.53, 6.0, "globular_cluster", "Sgr"),
    ("NGC7078", 322.493, 12.167, 6.20, 18.0, "globular_cluster", "Peg"),
    ("NGC7089", 323.363, -0.823, 6.47, 16.0, "globular_cluster", "Aqr"),
    ("NGC7099", 325.092, -23.180, 7.19, 12.0, "globular_cluster", "Cap"),
    ("IC434", 85.250, -2.400, 11.00, 60.0, "nebula", "Ori"),
    ("IC1396", 324.750, 57.500, 3.50, 170.0, "nebula", "Cep"),
    ("IC1805", 38.150, 61.450, 6.50, 60.0, "nebula", "Cas"),
    ("IC1848", 42.750, 60.400, 6.50, 60.0, "nebula", "Cas"),
    ("IC2118", 76.250, -7.050, 13.00, 180.0, "nebula", "Eri"),
    ("IC2177", 108.750, -10.500, 15.00, 20.0, "nebula", "Mon"),
    ("IC2944", 174.500, -63.367, 4.50, 75.0, "nebula", "Cen"),
    ("IC405", 79.750, 34.250, 10.00, 30.0, "nebula", "Aur"),
    ("IC410", 80.750, 33.500, 10.00, 40.0, "nebula", "Aur"),
    ("IC417", 82.750, 34.500, 10.00, 12.0, "nebula", "Aur"),
    ("IC443", 94.500, 22.650, 12.00, 50.0, "nebula", "Gem"),
    ("IC4604", 246.350, -23.433, 10.00, 60.0, "nebula", "Oph"),
    ("IC4628", 254.200, -40.200, 10.00, 90.0, "nebula", "Sco"),
    ("IC4703", 274.700, -13.807, 6.00, 35.0, "nebula", "Ser"),
    ("IC5067", 312.500, 44.333, 8.00, 25.0, "nebula", "Cyg"),
    ("IC5070", 313.000, 44.333, 8.00, 30.0, "nebula", "Cyg"),
    ("IC5146", 328.500, 47.267, 7.20, 12.0, "nebula", "Cyg"),
]


def init_database():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)

    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bright_stars (
            hr_number INTEGER PRIMARY KEY,
            name TEXT,
            ra_deg REAL,
            dec_deg REAL,
            mag REAL,
            spectral_type TEXT,
            con TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS galaxies (
            catalog_id TEXT PRIMARY KEY,
            ra_deg REAL,
            dec_deg REAL,
            mag REAL,
            size_arcmin REAL,
            obj_type TEXT,
            const TEXT,
            diffuse INTEGER DEFAULT 0,
            is_duplicate INTEGER DEFAULT 0,
            dec_filtered INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS download_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            catalog_name TEXT,
            source_url TEXT,
            status TEXT,
            file_size INTEGER,
            entry_count INTEGER,
            downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS catalog_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stat_name TEXT UNIQUE,
            stat_value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.executemany(
        "INSERT OR REPLACE INTO bright_stars VALUES (?, ?, ?, ?, ?, ?, ?)",
        BRIGHT_STARS
    )

    cursor.executemany(
        "INSERT OR REPLACE INTO galaxies VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0, 0)",
        NGC_IC_OBJECTS
    )

    cursor.execute(
        "INSERT INTO download_log (catalog_name, source_url, status, file_size, entry_count) VALUES (?, ?, ?, ?, ?)",
        ("BSC", "local://builtin", "success", 0, len(BRIGHT_STARS))
    )
    cursor.execute(
        "INSERT INTO download_log (catalog_name, source_url, status, file_size, entry_count) VALUES (?, ?, ?, ?, ?)",
        ("NGC_IC", "local://builtin", "success", 0, len(NGC_IC_OBJECTS))
    )

    cursor.execute(
        "INSERT OR REPLACE INTO catalog_stats (stat_name, stat_value) VALUES (?, ?)",
        ("total_stars", str(len(BRIGHT_STARS)))
    )
    cursor.execute(
        "INSERT OR REPLACE INTO catalog_stats (stat_name, stat_value) VALUES (?, ?)",
        ("total_galaxies", str(len(NGC_IC_OBJECTS)))
    )

    conn.commit()
    conn.close()

    size_kb = DB_PATH.stat().st_size / 1024
    print(f"星表数据库初始化完成: {DB_PATH}")
    print(f"  文件大小: {size_kb:.1f} KB")
    print(f"  明亮恒星: {len(BRIGHT_STARS)} 颗")
    print(f"  深空天体: {len(NGC_IC_OBJECTS)} 个")
    print(f"  总计: {len(BRIGHT_STARS) + len(NGC_IC_OBJECTS)} 个天体")


if __name__ == "__main__":
    init_database()
