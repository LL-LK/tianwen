"""
星表下载和管理模块 (Star Catalog Manager)
=========================================
支持离线下载和管理BSC(明亮星表)和NGC/IC目录
提供Dec过滤、NGC/IC去重和查询接口

参考: astronomy_algorithms.py 第863-871行的CATALOG_FILTER_PARAMS
"""
import logging
logger = logging.getLogger(__name__)

import urllib.request
import urllib.error
import gzip
import sqlite3
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any


# ============================================================
# 配置常量
# ============================================================

CATALOG_FILTER_PARAMS = {
    'initial_count': 100000,
    'dec_filter_deg': -36.086,          # 赤纬过滤阈值
    'after_dec_filter': 11443,
    'catalog_filter': ['NGC', 'IC', 'PGC', 'UGC', 'ESO'],
    'after_catalog_filter': 4773,
    'duplicate_tolerance_arcmin': 0.3,  # 去重容差 (角分)
    'final_count': 3772,
}

# BSC (Bright Star Catalog) FTP源
BSC_URLS = [
    'ftp://cdsarc.u-strasbg.fr/cats/V/50/gcws.gz',
    'https://heasarc.gsfc.nasa.gov/FTP/heasarc/dbase/wget/bsc5q.gz',
]

# NGC/IC 目录源
NGC_IC_URLS = [
    'https://heasarc.gsfc.nasa.gov/FTP/heasarc/dbase/wget/ngc_ic.gz',
    'http://cdsarc.u-strasbg.fr/cats/VI/67/ngc_ic.gz',
]

# 数据目录
DEFAULT_DATA_DIR = Path(__file__).parent / 'data' / 'star_catalogs'
DEFAULT_DB_PATH = Path(__file__).parent / 'data' / 'star_catalogs.db'


# ============================================================
# 数据模型
# ============================================================

@dataclass
class StarEntry:
    """BSC星表条目"""
    hr_number: int           # HR编号
    name: str                # 名称
    ra_deg: float            # 赤经 (度)
    dec_deg: float           # 赤纬 (度)
    mag: float               # 星等
    spectral_type: str       # 光谱类型
    con: str                 # 星座
    
    @property
    def dec_filter_pass(self) -> bool:
        """检查是否通过赤纬过滤"""
        return self.dec_deg >= CATALOG_FILTER_PARAMS['dec_filter_deg']


@dataclass
class GalaxyEntry:
    """NGC/IC星系条目"""
    catalog_id: str          # NGC/IC编号
    ra_deg: float            # 赤经 (度)
    dec_deg: float           # 赤纬 (度)
    mag: float               # 视星等
    size_arcmin: float       # 角大小 (角分)
    obj_type: str            # 天体类型
    const: str               # 星座
    diffuse: bool = False    # 是否弥散
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'catalog_id': self.catalog_id,
            'ra_deg': self.ra_deg,
            'dec_deg': self.dec_deg,
            'mag': self.mag,
            'size_arcmin': self.size_arcmin,
            'obj_type': self.obj_type,
            'const': self.const,
            'diffuse': self.diffuse,
        }


# ============================================================
# 下载器
# ============================================================

class CatalogDownloader:
    """星表下载器"""
    
    def __init__(self, data_dir: Path = DEFAULT_DATA_DIR):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._log = []
        
    def download_with_retry(self, urls: List[str], dest_path: Path, 
                           max_retries: int = 3) -> Tuple[bool, str]:
        """尝试从多个源下载，自动重试"""
        for url in urls:
            for attempt in range(max_retries):
                try:
                    return self._download_file(url, dest_path)
                except Exception as e:
                    self._log.append(f"[尝试 {attempt+1}/{max_retries}] {url}: {e}")
                    continue
        return False, "所有下载源均失败"
    
    def _download_file(self, url: str, dest_path: Path) -> Tuple[bool, str]:
        """下载文件"""
        self._log.append(f"开始下载: {url}")
        
        # 使用urllib标准库下载
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (StarCatalogManager/1.0)'
        })
        
        with urllib.request.urlopen(req, timeout=60) as response:
            content = response.read()
            
            # 如果是gz压缩文件，先解压
            if url.endswith('.gz'):
                decompressed = gzip.decompress(content)
                dest_path = dest_path.with_suffix('')
                dest_path.write_bytes(decompressed)
            else:
                dest_path.write_bytes(content)
        
        size = dest_path.stat().st_size
        self._log.append(f"下载完成: {dest_path.name} ({size/1024:.1f} KB)")
        return True, f"成功下载到 {dest_path}"
    
    def get_log(self) -> List[str]:
        return self._log.copy()


# ============================================================
# BSC解析器
# ============================================================

class BSCParser:
    """
    解析BSC (Bright Star Catalog) 格式
    格式说明: 根据 BSC5q 文档
    """
    
    @staticmethod
    def parse_line(line: str) -> Optional[StarEntry]:
        """解析单行BSC数据"""
        if len(line) < 81:
            return None
            
        try:
            # HR编号 (1-4)
            hr_number = int(line[0:4].strip())
            
            # 赤经 (RA) 5-12: HHMMSS.ss
            ra_str = line[4:12].strip()
            ra_deg = BSCParser._ra_to_degrees(ra_str)
            
            # 赤纬 (Dec) 13-23: sDDMMSS
            dec_str = line[12:22].strip()
            dec_deg = BSCParser._dec_to_degrees(dec_str)
            
            # 星等 (Vmag) 33-37
            mag_str = line[32:37].strip()
            mag = float(mag_str) if mag_str else 99.0
            
            # 光谱类型 38-43
            spectral_type = line[37:43].strip()
            
            # 星座代码 48-50
            con = line[47:50].strip()
            
            # 名称
            name = f"HR{hr_number}"
            
            return StarEntry(
                hr_number=hr_number,
                name=name,
                ra_deg=ra_deg,
                dec_deg=dec_deg,
                mag=mag,
                spectral_type=spectral_type,
                con=con
            )
        except (ValueError, IndexError):
            return None
    
    @staticmethod
    def _ra_to_degrees(ra_str: str) -> float:
        """将HHMMSS.ss格式转换为度"""
        try:
            hours = float(ra_str[:2])
            mins = float(ra_str[2:4])
            secs = float(ra_str[4:]) if len(ra_str) > 4 else 0.0
            return (hours + mins/60 + secs/3600) * 15.0
        except ValueError:
            return 0.0
    
    @staticmethod
    def _dec_to_degrees(dec_str: str) -> float:
        """将sDDMMSS格式转换为度"""
        try:
            sign = -1 if dec_str[0] == '-' else 1
            deg = float(dec_str[1:3])
            mins = float(dec_str[3:5])
            secs = float(dec_str[5:]) if len(dec_str) > 5 else 0.0
            return sign * (deg + mins/60 + secs/3600)
        except ValueError:
            return 0.0
    
    @staticmethod
    def parse_file(file_path: Path) -> List[StarEntry]:
        """解析整个BSC文件"""
        entries = []
        lines = file_path.read_text().splitlines()
        for line in lines:
            entry = BSCParser.parse_line(line)
            if entry:
                entries.append(entry)
        return entries


# ============================================================
# NGC/IC解析器
# ============================================================

class NGCICParser:
    """
    解析NGC/IC目录
    """
    
    @staticmethod
    def parse_line(line: str) -> Optional[GalaxyEntry]:
        """解析单行NGC/IC数据"""
        if len(line) < 80:
            return None
            
        try:
            # NGC/IC编号
            catalog_id = line[0:9].strip()
            
            # RA (赤经)
            ra_str = line[18:29].strip()
            ra_deg = NGCICParser._ra_to_degrees(ra_str)
            
            # Dec (赤纬)
            dec_str = line[30:41].strip()
            dec_deg = NGCICParser._dec_to_degrees(dec_str)
            
            # 星等
            mag_str = line[41:47].strip()
            mag = float(mag_str) if mag_str else 99.0
            
            # 角大小
            size_str = line[47:54].strip()
            size_arcmin = float(size_str) if size_str else 0.0
            
            # 类型
            obj_type = line[54:58].strip()
            
            # 星座
            const = line[60:63].strip()
            
            return GalaxyEntry(
                catalog_id=catalog_id,
                ra_deg=ra_deg,
                dec_deg=dec_deg,
                mag=mag,
                size_arcmin=size_arcmin,
                obj_type=obj_type,
                const=const
            )
        except (ValueError, IndexError):
            return None
    
    @staticmethod
    def _ra_to_degrees(ra_str: str) -> float:
        """将RA字符串转换为度"""
        try:
            parts = ra_str.split()
            if len(parts) >= 3:
                h = float(parts[0])
                m = float(parts[1])
                s = float(parts[2])
                return (h + m/60 + s/3600) * 15.0
        except ValueError:
            pass
        return 0.0
    
    @staticmethod
    def _dec_to_degrees(dec_str: str) -> float:
        """将Dec字符串转换为度"""
        try:
            parts = dec_str.split()
            if len(parts) >= 3:
                sign = -1 if parts[0].startswith('-') else 1
                d = float(parts[0].replace('-', ''))
                m = float(parts[1])
                s = float(parts[2])
                return sign * (d + m/60 + s/3600)
        except ValueError:
            pass
        return 0.0
    
    @staticmethod
    def parse_file(file_path: Path) -> List[GalaxyEntry]:
        """解析整个NGC/IC文件"""
        entries = []
        lines = file_path.read_text().splitlines()
        for line in lines:
            entry = NGCICParser.parse_line(line)
            if entry:
                entries.append(entry)
        return entries


# ============================================================
# 去重算法
# ============================================================

class DuplicateRemover:
    """天体去重算法"""
    
    @staticmethod
    def angular_separation(ra1: float, dec1: float, 
                           ra2: float, dec2: float) -> float:
        """
        计算两天体之间的角距离 (度)
        使用Vincenty公式
        """
        import math
        ra1_rad = math.radians(ra1)
        dec1_rad = math.radians(dec1)
        ra2_rad = math.radians(ra2)
        dec2_rad = math.radians(dec2)
        
        delta_ra = ra2_rad - ra1_rad
        
        cos_dec1 = math.cos(dec1_rad)
        sin_dec1 = math.sin(dec1_rad)
        cos_dec2 = math.cos(dec2_rad)
        sin_dec2 = math.sin(dec2_rad)
        cos_delta_ra = math.cos(delta_ra)
        sin_delta_ra = math.sin(delta_ra)
        
        numerator = math.sqrt(
            (cos_dec2 * sin_delta_ra)**2 + 
            (cos_dec1 * sin_dec2 - sin_dec1 * cos_dec2 * cos_delta_ra)**2
        )
        denominator = sin_dec1 * sin_dec2 + cos_dec1 * cos_dec2 * cos_delta_ra
        
        return math.degrees(math.atan2(numerator, denominator))
    
    @staticmethod
    def remove_duplicates(galaxies: List[GalaxyEntry],
                         tolerance_arcmin: float = 0.3) -> List[GalaxyEntry]:
        """
        对NGC/IC星系列表去重
        tolerance_arcmin: 容差 (角分)
        """
        tolerance_deg = tolerance_arcmin / 60.0
        keep_indices = set()
        
        galaxies_with_idx = list(enumerate(galaxies))
        
        for i, gal1 in galaxies_with_idx:
            if i in keep_indices:
                continue
            
            keep_indices.add(i)
            
            for j, gal2 in galaxies_with_idx[i+1:]:
                if j in keep_indices:
                    continue
                    
                sep = DuplicateRemover.angular_separation(
                    gal1.ra_deg, gal1.dec_deg,
                    gal2.ra_deg, gal2.dec_deg
                )
                
                if sep < tolerance_deg:
                    # j是gal1的重复，标记移除
                    pass
        
        return [galaxies[i] for i in sorted(keep_indices)]
    
    @staticmethod
    def deduplicate_ngcic(ngc_entries: List[GalaxyEntry],
                         ic_entries: List[GalaxyEntry],
                         tolerance_arcmin: float = 0.3) -> List[GalaxyEntry]:
        """
        NGC和IC交叉去重
        如果同一个天体同时出现在NGC和IC中，优先保留NGC
        """
        tolerance_deg = tolerance_arcmin / 60.0
        result = []
        ngc_ids = {g.catalog_id for g in ngc_entries}
        
        # 先添加所有NGC
        result.extend(ngc_entries)
        added_positions = [(g.ra_deg, g.dec_deg) for g in ngc_entries]
        
        # 检查IC中是否有重复
        for ic_gal in ic_entries:
            is_duplicate = False
            
            # 检查是否在NGC中已存在
            if ic_gal.catalog_id.replace('IC', 'NGC') in ngc_ids:
                continue
            
            # 检查位置是否接近NGC
            for ra, dec in added_positions:
                sep = DuplicateRemover.angular_separation(
                    ic_gal.ra_deg, ic_gal.dec_deg, ra, dec
                )
                if sep < tolerance_deg:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                result.append(ic_gal)
                added_positions.append((ic_gal.ra_deg, ic_gal.dec_deg))
        
        return result


# ============================================================
# SQLite存储
# ============================================================

class CatalogDatabase:
    """星表SQLite数据库"""
    
    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bright_stars (
                    hr_number INTEGER PRIMARY KEY,
                    name TEXT,
                    ra_deg REAL,
                    dec_deg REAL,
                    mag REAL,
                    spectral_type TEXT,
                    con TEXT,
                    dec_filtered INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS galaxies (
                    catalog_id TEXT PRIMARY KEY,
                    ra_deg REAL,
                    dec_deg REAL,
                    mag REAL,
                    size_arcmin REAL,
                    obj_type TEXT,
                    const TEXT,
                    diffuse INTEGER DEFAULT 0,
                    dec_filtered INTEGER DEFAULT 0,
                    is_duplicate INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS download_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    catalog_type TEXT,
                    url TEXT,
                    status TEXT,
                    file_size INTEGER,
                    record_count INTEGER,
                    downloaded_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_stars_dec 
                ON bright_stars(dec_deg)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_galaxies_dec 
                ON galaxies(dec_deg)
            """)
    
    def insert_stars(self, stars: List[StarEntry]):
        with sqlite3.connect(self.db_path) as conn:
            for star in stars:
                conn.execute("""
                    INSERT OR REPLACE INTO bright_stars 
                    (hr_number, name, ra_deg, dec_deg, mag, spectral_type, con)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (star.hr_number, star.name, star.ra_deg, star.dec_deg,
                      star.mag, star.spectral_type, star.con))
    
    def insert_galaxies(self, galaxies: List[GalaxyEntry]):
        with sqlite3.connect(self.db_path) as conn:
            for gal in galaxies:
                conn.execute("""
                    INSERT OR REPLACE INTO galaxies 
                    (catalog_id, ra_deg, dec_deg, mag, size_arcmin, obj_type, const)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (gal.catalog_id, gal.ra_deg, gal.dec_deg,
                      gal.mag, gal.size_arcmin, gal.obj_type, gal.const))
    
    def mark_dec_filtered_stars(self, min_dec: float):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE bright_stars SET dec_filtered=1 WHERE dec_deg >= ?",
                (min_dec,)
            )
    
    def mark_dec_filtered_galaxies(self, min_dec: float):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE galaxies SET dec_filtered=1 WHERE dec_deg >= ?",
                (min_dec,)
            )
    
    def mark_duplicates(self, duplicate_ids: List[str]):
        with sqlite3.connect(self.db_path) as conn:
            for gid in duplicate_ids:
                conn.execute(
                    "UPDATE galaxies SET is_duplicate=1 WHERE catalog_id=?",
                    (gid,)
                )
    
    def query_stars(self, min_dec: Optional[float] = None,
                   max_dec: Optional[float] = None,
                   min_mag: Optional[float] = None,
                   max_mag: Optional[float] = None,
                   limit: int = 1000) -> List[Dict]:
        """查询BSC星表"""
        query = "SELECT * FROM bright_stars WHERE 1=1"
        params = []
        
        if min_dec is not None:
            query += " AND dec_deg >= ?"
            params.append(min_dec)
        if max_dec is not None:
            query += " AND dec_deg <= ?"
            params.append(max_dec)
        if min_mag is not None:
            query += " AND mag >= ?"
            params.append(min_mag)
        if max_mag is not None:
            query += " AND mag <= ?"
            params.append(max_mag)
        
        query += f" ORDER BY mag ASC LIMIT {limit}"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def query_galaxies(self, min_dec: Optional[float] = None,
                      max_dec: Optional[float] = None,
                      min_mag: Optional[float] = None,
                      max_mag: Optional[float] = None,
                      exclude_duplicates: bool = True,
                      limit: int = 1000) -> List[Dict]:
        """查询NGC/IC星表"""
        query = "SELECT * FROM galaxies WHERE 1=1"
        params = []
        
        if min_dec is not None:
            query += " AND dec_deg >= ?"
            params.append(min_dec)
        if max_dec is not None:
            query += " AND dec_deg <= ?"
            params.append(max_dec)
        if min_mag is not None:
            query += " AND mag >= ?"
            params.append(min_mag)
        if max_mag is not None:
            query += " AND mag <= ?"
            params.append(max_mag)
        if exclude_duplicates:
            query += " AND is_duplicate=0"
        
        query += f" ORDER BY mag ASC LIMIT {limit}"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM bright_stars) as star_count,
                    (SELECT COUNT(*) FROM bright_stars WHERE dec_filtered=1) as star_filtered,
                    (SELECT COUNT(*) FROM galaxies) as galaxy_count,
                    (SELECT COUNT(*) FROM galaxies WHERE dec_filtered=1) as galaxy_filtered,
                    (SELECT COUNT(*) FROM galaxies WHERE is_duplicate=1) as duplicate_count
            """)
            row = cursor.fetchone()
            return {
                'star_count': row[0],
                'star_filtered': row[1],
                'galaxy_count': row[2],
                'galaxy_filtered': row[3],
                'duplicate_count': row[4]
            }
    
    def log_download(self, catalog_type: str, url: str, 
                     status: str, file_size: int, record_count: int):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO download_log 
                (catalog_type, url, status, file_size, record_count)
                VALUES (?, ?, ?, ?, ?)
            """, (catalog_type, url, status, file_size, record_count))


# ============================================================
# 主管理器
# ============================================================

class StarCatalogManager:
    """
    星表管理器
    整合下载、解析、过滤、去重、存储和查询
    """
    
    def __init__(self, data_dir: Path = DEFAULT_DATA_DIR):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.db = CatalogDatabase()
        self.downloader = CatalogDownloader(data_dir)
        
        # 过滤参数
        self.dec_filter_deg = CATALOG_FILTER_PARAMS['dec_filter_deg']
        self.dup_tolerance_arcmin = CATALOG_FILTER_PARAMS['duplicate_tolerance_arcmin']
    
    def download_bsc(self) -> Tuple[bool, str]:
        """下载明亮星表(BSC)"""
        bsc_path = self.data_dir / 'bsc5q'
        success, msg = self.downloader.download_with_retry(BSC_URLS, bsc_path)
        
        if success:
            # 解析并存储
            entries = BSCParser.parse_file(bsc_path)
            self.db.insert_stars(entries)
            self.db.log_download('BSC', BSC_URLS[0], 'success',
                                bsc_path.stat().st_size, len(entries))
            return True, f"下载并解析了 {len(entries)} 颗星"
        
        self.db.log_download('BSC', BSC_URLS[0], 'failed', 0, 0)
        return False, msg
    
    def download_ngcic(self) -> Tuple[bool, str]:
        """下载NGC/IC目录"""
        ngcic_path = self.data_dir / 'ngc_ic'
        success, msg = self.downloader.download_with_retry(NGC_IC_URLS, ngcic_path)
        
        if success:
            # 解析并存储
            entries = NGCICParser.parse_file(ngcic_path)
            
            # 分类NGC和IC
            ngc_entries = [e for e in entries if e.catalog_id.startswith('NGC')]
            ic_entries = [e for e in entries if e.catalog_id.startswith('IC')]
            
            self.db.insert_galaxies(entries)
            self.db.log_download('NGC_IC', NGC_IC_URLS[0], 'success',
                                ngcic_path.stat().st_size, len(entries))
            return True, f"下载并解析了 {len(entries)} 个天体 (NGC: {len(ngc_entries)}, IC: {len(ic_entries)})"
        
        self.db.log_download('NGC_IC', NGC_IC_URLS[0], 'failed', 0, 0)
        return False, msg
    
    def apply_filters(self) -> Dict[str, int]:
        """
        应用过滤条件
        1. Dec过滤 (赤纬 >= dec_filter_deg)
        2. NGC/IC去重
        """
        stats = {}
        
        # 获取所有星系
        all_galaxies = self.db.query_galaxies(exclude_duplicates=False, limit=100000)
        
        # 应用Dec过滤
        filtered = [g for g in all_galaxies if g['dec_deg'] >= self.dec_filter_deg]
        self.db.mark_dec_filtered_galaxies(self.dec_filter_deg)
        stats['after_dec_filter'] = len(filtered)
        
        # 去重
        galaxy_entries = [
            GalaxyEntry(
                catalog_id=g['catalog_id'],
                ra_deg=g['ra_deg'],
                dec_deg=g['dec_deg'],
                mag=g['mag'],
                size_arcmin=g['size_arcmin'],
                obj_type=g['obj_type'],
                const=g['const']
            )
            for g in filtered
        ]
        
        # 分离NGC和IC
        ngc_entries = [g for g in galaxy_entries if g.catalog_id.startswith('NGC')]
        ic_entries = [g for g in galaxy_entries if g.catalog_id.startswith('IC')]
        
        # 交叉去重
        deduped = DuplicateRemover.deduplicate_ngcic(
            ngc_entries, ic_entries, self.dup_tolerance_arcmin
        )
        
        # 标记重复
        deduped_ids = {g.catalog_id for g in deduped}
        duplicate_ids = [g['catalog_id'] for g in filtered 
                       if g['catalog_id'] not in deduped_ids]
        self.db.mark_duplicates(duplicate_ids)
        
        stats['after_dedup'] = len(deduped)
        stats['duplicates_removed'] = len(duplicate_ids)
        
        return stats
    
    def query(self, catalog_type: str = 'all', **kwargs) -> List[Dict]:
        """
        查询接口
        
        Args:
            catalog_type: 'bsc' | 'ngcic' | 'all'
            **kwargs: 查询参数 (min_dec, max_dec, min_mag, max_mag, limit)
        
        Returns:
            查询结果列表
        """
        results = []
        
        if catalog_type in ('bsc', 'all'):
            results.extend(self.db.query_stars(**kwargs))
        
        if catalog_type in ('ngcic', 'all'):
            results.extend(self.db.query_galaxies(**kwargs))
        
        return results
    
    def query_by_position(self, ra_deg: float, dec_deg: float,
                         radius_deg: float = 1.0,
                         catalog_type: str = 'all') -> List[Dict]:
        """
        按位置查询 (天区搜索)
        
        Args:
            ra_deg: 中心赤经 (度)
            dec_deg: 中心赤纬 (度)
            radius_deg: 搜索半径 (度)
            catalog_type: 'bsc' | 'ngcic' | 'all'
        """
        results = []
        
        _ = ra_deg - radius_deg
        _ = ra_deg + radius_deg
        min_dec = dec_deg - radius_deg
        max_dec = dec_deg + radius_deg
        
        kwargs = {'min_dec': min_dec, 'max_dec': max_dec, 'limit': 10000}
        
        if catalog_type in ('bsc', 'all'):
            stars = self.db.query_stars(**kwargs)
            # 球面距离过滤
            for star in stars:
                sep = DuplicateRemover.angular_separation(
                    ra_deg, dec_deg, star['ra_deg'], star['dec_deg']
                )
                if sep <= radius_deg:
                    star['separation_deg'] = sep
                    results.append(star)
        
        if catalog_type in ('ngcic', 'all'):
            galaxies = self.db.query_galaxies(**kwargs)
            for gal in galaxies:
                sep = DuplicateRemover.angular_separation(
                    ra_deg, dec_deg, gal['ra_deg'], gal['dec_deg']
                )
                if sep <= radius_deg:
                    gal['separation_deg'] = sep
                    results.append(gal)
        
        # 按角距离排序
        results.sort(key=lambda x: x['separation_deg'])
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        base_stats = self.db.get_stats()
        base_stats['dec_filter_deg'] = self.dec_filter_deg
        base_stats['dup_tolerance_arcmin'] = self.dup_tolerance_arcmin
        return base_stats
    
    def is_catalog_ready(self) -> Dict[str, bool]:
        """检查各星表是否已下载"""
        bsc_exists = (self.data_dir / 'bsc5q').exists()
        ngcic_exists = (self.data_dir / 'ngc_ic').exists()
        
        return {
            'bsc': bsc_exists,
            'ngcic': ngcic_exists
        }
    
    def get_download_log(self) -> List[Dict]:
        """获取下载日志"""
        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM download_log ORDER BY downloaded_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    def lookup(self, target: str) -> Optional[Dict]:
        """按名称查找天体"""
        target_upper = target.upper().strip()
        stars = self.db.query_stars(limit=10000)
        for s in stars:
            if s.get('name', '').upper() == target_upper:
                return s
        galaxies = self.db.query_galaxies(limit=10000)
        for g in galaxies:
            if g.get('catalog_id', '').upper() == target_upper:
                return g
        return None

    def list_all(self, type_filter: str = None) -> List[Dict]:
        """列出所有天体，兼容旧API"""
        results = []
        if type_filter is None or type_filter in ('star', 'bsc'):
            results.extend(self.db.query_stars(limit=10000))
        if type_filter is None or type_filter in ('galaxy', 'nebula', 'cluster', 'ngcic'):
            results.extend(self.db.query_galaxies(limit=10000))
        return results


# ============================================================
# 便捷函数
# ============================================================

def create_default_manager() -> StarCatalogManager:
    """创建默认管理器实例"""
    return StarCatalogManager(DEFAULT_DATA_DIR)


def quick_download() -> Tuple[bool, str]:
    """一键下载所有星表"""
    manager = create_default_manager()
    
    success, msg = manager.download_bsc()
    if not success:
        return False, f"BSC下载失败: {msg}"
    
    success, msg = manager.download_ngcic()
    if not success:
        return False, f"NGC/IC下载失败: {msg}"
    
    return True, "所有星表下载完成"


if __name__ == '__main__':
    # 测试/演示
    manager = StarCatalogManager()
    
    logger.debug("=" * 50)
    logger.info("星表管理器 (Star Catalog Manager)")
    logger.debug("=" * 50)
    logger.info(f"数据目录: {manager.data_dir}")
    logger.info(f"数据库: {manager.db.db_path}")
    logger.info(f"Dec过滤阈值: {manager.dec_filter_deg}°")
    logger.info(f"去重容差: {manager.dup_tolerance_arcmin}'")
    logger.debug("")
    
    # 检查状态
    ready = manager.is_catalog_ready()
    logger.info("星表状态:")
    logger.info(f"  BSC: {'已下载' if ready['bsc'] else '未下载'}")
    logger.info(f"  NGC/IC: {'已下载' if ready['ngcic'] else '未下载'}")
    logger.debug("")
    
    # 演示查询
    if ready['bsc']:
        stars = manager.db.query_stars(max_mag=6.0, limit=10)
        logger.info(f"亮星查询 (V<6): {len(stars)} 颗")
        for s in stars[:5]:
            logger.info(f"  {s['name']}: RA={s['ra_deg']:.2f}°, Dec={s['dec_deg']:.2f}°, V={s['mag']}")
    
    if ready['ngcic']:
        galaxies = manager.db.query_galaxies(max_mag=14.0, limit=10)
        logger.info(f"\n亮星系查询 (V<14): {len(galaxies)} 个")
        for g in galaxies[:5]:
            logger.info(f"  {g['catalog_id']}: RA={g['ra_deg']:.2f}°, Dec={g['dec_deg']:.2f}°, V={g['mag']}")
    
    logger.info("\n统计信息:")
    stats = manager.get_stats()
    for k, v in stats.items():
        logger.info(f"  {k}: {v}")
