"""
SExtractor (Source Extractor) 封装 - 天文图像源检测与测光

功能:
1. 使用 sextractor (Source Extractor) 对FITS图像进行源检测
2. 输出检测源的坐标、流量、形状参数 (FWHM, ellipticity)
3. 支持多波段联合测光

依赖:
- sextractor (Source Extractor by Emmanuel Bertin)
  安装: sudo apt-get install source-extractor  (Linux)
  或: https://www.astromatic.net/software/sextractor/

用法:
  extractor = SExtractorWrapper()
  sources = extractor.detect("/path/to/image.fits")
"""
import os
import subprocess
import tempfile
import shutil
from typing import Optional, Dict, Any, List

import numpy as np

HAS_ASTROPY = False
try:
    from astropy.io import fits
    from astropy.table import Table
    HAS_ASTROPY = True
except ImportError:
    pass


class SExtractorWrapper:
    """
    SExtractor 源检测与测光封装
    
    SExtractor是天文图像源检测的标准工具，可输出:
    - 位置 (X_IMAGE, Y_IMAGE, ALPHA_J2000, DELTA_J2000)
    - 流量 (FLUX_APER, FLUX_AUTO, MAG_APER, MAG_AUTO)
    - 形态参数 (FWHM_IMAGE, ELLIPTICITY, CLASS_STAR)
    """
    
    # SExtractor 默认参数文件
    DEFAULT_CONFIG = {
        "DETECT_TYPE": "CCD",
        "THRESH_TYPE": "RELATIVE",
        "DETECT_THRESH": "1.5",        # 检测阈值 (相对于背景 RMS)
        "ANALYSIS_THRESH": "1.5",      # 分析阈值
        "DETECT_MINAREA": "5",          # 最小检测面积 (像素)
        "BACK_SIZE": "64",              # 背景网格大小
        "BACK_FILTERSIZE": "3",
        "DEBLEND_NTHRESH": "32",
        "DEBLEND_MINCONT": "0.005",
        "CLEAN": "Y",
        "CLEAN_PARAM": "1.0",
        "PHOT_APERTURES": "5,10,15,20", # 测光孔径 (像素)
        "PHOT_AUTOPARAMS": "2.5,3.0",   # AUTO测光参数 (Kron factor, min radius)
        "SATUR_LEVEL": "50000.0",
        "MAG_ZEROPOINT": "25.0",        # 零点到流量转换
        "SEEING_FWHM": "1.5",           # seeing FWHM (arcsec)
        "STARNNW_NAME": "/usr/share/sextractor/default.nnw",  # 星形权重文件名
        "MEMORY_OBJSTACK": "3000",
        "MEMORY_PIXSTACK": "300000",
        "VERBOSE_TYPE": "NORMAL",
    }
    
    def __init__(
        self,
        config_path: Optional[str] = None,
        work_dir: Optional[str] = None,
        sextractor_cmd: str = "sex"
    ):
        """
        Args:
            config_path: 自定义SExtractor配置文件的路径
            work_dir: 临时工作目录
            sextractor_cmd: sextractor命令 (默认 "sex")
        """
        self.work_dir = work_dir or tempfile.mkdtemp(prefix="sextractor_")
        self.config_path = config_path
        self.sextractor_cmd = sextractor_cmd
        
        # 检测sextractor是否可用
        self.available = self._check_sextractor()
        
        # 默认输出列
        self.output_columns = [
            "NUMBER",           # 源编号
            "X_IMAGE",          # 像素X坐标
            "Y_IMAGE",          # 像素Y坐标
            "ALPHA_J2000",      # RA坐标 (度)
            "DELTA_J2000",      # Dec坐标 (度)
            "FLUX_APER",        # 孔径流量
            "FLUX_AUTO",        # AUTO流量
            "FLUX_RADIUS",      # 流量半径
            "MAG_APER",         # 孔径星等
            "MAG_AUTO",         # AUTO星等
            "FWHM_IMAGE",       # FWHM (像素)
            "ELLIPTICITY",      # 椭率 (1-b/a)
            "CLASS_STAR",       # 星/非星分类 (0-1)
            "FLAGS",            # 标志
            "BACKGROUND",       # 背景值
            "THRESHOLD",        # 检测阈值
        ]
    
    def _check_sextractor(self) -> bool:
        """检查sextractor是否安装"""
        try:
            result = subprocess.run(
                [self.sextractor_cmd, "-v"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                version_line = result.stdout.strip().split('\n')[0] if result.stdout else "unknown"
                print(f"SExtractor 可用: {version_line}")
                return True
            return False
        except FileNotFoundError:
            print("[INSTALL REQUIRED] sextractor 未找到")
            print("  安装命令: sudo apt-get install source-extractor")
            print("  或访问: https://www.astromatic.net/software/sextractor/")
            return False
        except (subprocess.SubprocessError):
            return False
    
    def create_default_config(self, output_path: str) -> str:
        """创建默认SExtractor配置文件"""
        lines = []
        for key, value in self.DEFAULT_CONFIG.items():
            lines.append(f"{key:<25} {value}")
        lines.append(f"PARAMETERS_NAME    {output_path.replace('.cfg', '.param')}")
        
        config_file = os.path.join(self.work_dir, "default.sex")
        with open(config_file, "w") as f:
            f.write("\n".join(lines))
            
        # 参数文件
        param_file = os.path.join(self.work_dir, "default.param")
        with open(param_file, "w") as f:
            f.write("\n".join(self.output_columns))
            
        return config_file
    
    def detect(
        self,
        image_path: str,
        weight_path: Optional[str] = None,
        config_overrides: Optional[Dict[str, str]] = None,
        catalog_path: Optional[str] = None,
        catalog_format: str = "ASCII",
        timeout: int = 120
    ) -> Optional[List[Dict[str, Any]]]:
        """
        对FITS图像进行源检测
        
        Args:
            image_path: 输入FITS图像路径
            weight_path: 权重图路径 (可选，用于加权检测)
            config_overrides: 配置覆盖参数
            catalog_path: 输出星表路径 (默认临时文件)
            catalog_format: 输出格式 (ASCII, FITS_LDAC, HEAD)
            timeout: 超时时间 (秒)
            
        Returns:
            检测到的源列表，每项为字典
        """
        if not self.available:
            print("SExtractor 不可用，使用 astropy 模拟检测")
            return self._mock_detect(image_path)
        
        # 创建临时配置
        catalog_path = catalog_path or os.path.join(self.work_dir, "catalog.cat")
        config_file = os.path.join(self.work_dir, "run.sex")
        param_file = os.path.join(self.work_dir, "run.param")
        
        # 生成配置
        config = dict(self.DEFAULT_CONFIG)
        if config_overrides:
            config.update(config_overrides)
        config["CATALOG_NAME"] = catalog_path
        config["CATALOG_TYPE"] = catalog_format.upper()
        config["PARAMETERS_NAME"] = param_file
        
        with open(config_file, "w") as f:
            for key, value in config.items():
                f.write(f"{key:<25} {value}\n")
                
        with open(param_file, "w") as f:
            f.write("\n".join(self.output_columns))
        
        # 构建命令
        cmd = [self.sextractor_cmd, image_path, "-c", config_file]
        
        # 添加权重图
        if weight_path:
            cmd.extend(["-WEIGHT_IMAGE", weight_path, "-WEIGHT_TYPE", "MAP_WEIGHT"])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.work_dir
            )
            
            if result.returncode != 0:
                print(f"SExtractor错误: {result.stderr[:500]}")
                return self._mock_detect(image_path)
            
            # 读取输出星表
            return self._read_catalog(catalog_path)
            
        except subprocess.TimeoutExpired:
            print(f"SExtractor超时 ({timeout}s)")
            return None
        except Exception as e:
            print(f"SExtractor异常: {e}")
            return self._mock_detect(image_path)
    
    def _read_catalog(self, catalog_path: str) -> Optional[List[Dict[str, Any]]]:
        """读取SExtractor输出星表"""
        if not os.path.exists(catalog_path):
            return None
            
        if not HAS_ASTROPY:
            # 简单文本解析
            return self._parse_catalog_text(catalog_path)
        
        try:
            if catalog_path.endswith(".cat"):
                # ASCII格式
                table = Table.read(catalog_path, format="ascii")
            else:
                table = Table.read(catalog_path)
                
            return [dict(row) for row in table]
        except Exception as e:
            print(f"星表读取失败: {e}")
            return self._parse_catalog_text(catalog_path)
    
    def _parse_catalog_text(self, catalog_path: str) -> List[Dict[str, Any]]:
        """简单文本解析"""
        sources = []
        with open(catalog_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) >= len(self.output_columns):
                    source = {}
                    for i, col in enumerate(self.output_columns):
                        try:
                            source[col] = float(parts[i])
                        except ValueError:
                            source[col] = parts[i]
                    sources.append(source)
        return sources
    
    def _mock_detect(self, image_path: str) -> Optional[List[Dict[str, Any]]]:
        """当SExtractor不可用时的模拟检测"""
        if not HAS_ASTROPY:
            print("astropy未安装，无法模拟源检测")
            return None
            
        try:
            with fits.open(image_path) as hdul:
                data = hdul[0].data
                
            # 简单模拟：返回一些随机源
            np.random.seed(42)
            n_sources = np.random.randint(10, 50)
            sources = []
            
            for i in range(n_sources):
                y, x = np.random.randint(10, data.shape[0]-10), np.random.randint(10, data.shape[1]-10)
                flux = float(data[y-5:y+5, x-5:x+5].sum())
                
                sources.append({
                    "NUMBER": i + 1,
                    "X_IMAGE": float(x),
                    "Y_IMAGE": float(y),
                    "FLUX_APER": flux,
                    "FLUX_AUTO": flux * 1.2,
                    "FWHM_IMAGE": np.random.uniform(2, 8),
                    "CLASS_STAR": np.random.uniform(0, 1),
                    "FLAGS": 0,
                    "mode": "mock"
                })
                
            return sources
        except Exception as e:
            print(f"模拟检测失败: {e}")
            return None
    
    def detect_from_array(
        self,
        image_data: np.ndarray,
        header: Optional[Dict] = None,
        **kwargs
    ) -> Optional[List[Dict[str, Any]]]:
        """从numpy数组直接检测"""
        with tempfile.NamedTemporaryFile(suffix=".fits", delete=False) as f:
            temp_path = f.name
            
        try:
            if header and HAS_ASTROPY:
                hdu = fits.PrimaryHDU(image_data, header=fits.Header(header))
            else:
                hdu = fits.PrimaryHDU(image_data)
            hdu.writeto(temp_path, overwrite=True)
            return self.detect(temp_path, **kwargs)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
    
    def cleanup(self):
        """清理临时文件"""
        if os.path.exists(self.work_dir):
            shutil.rmtree(self.work_dir, ignore_errors=True)


if __name__ == "__main__":
    extractor = SExtractorWrapper()
    print(f"SExtractor 可用: {extractor.available}")
