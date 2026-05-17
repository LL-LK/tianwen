"""
astrometry.net 求解器封装 - FITS图像 Plate-Solving

功能:
1. 使用 astrometry-engine (astrometry.net) 对FITS图像进行解析对位
2. 计算图像的 WCS (World Coordinate System) 坐标
3. 支持离线星表匹配

依赖:
- astrometry-engine (astrometry.net 的命令行工具)
- 可选: astropy.io.fits, numpy

安装 (Linux):
  sudo apt-get install astrometry-engine
  # 或从源码编译: https://github.com/dstndstn/astrometry.net

安装 (macOS):
  brew install astrometry-net

用法:
  solver = AstrometrySolver()
  result = solver.solve("/path/to/image.fits")
"""
import logging
logger = logging.getLogger(__name__)
import os
import subprocess
import tempfile
import shutil
from typing import Optional, Dict, Any, List

import numpy as np

HAS_ASTROPY = False
try:
    from astropy.io import fits
    import astropy.wcs as wcsmod
    HAS_ASTROPY = True
except ImportError:
    pass


# astrometry.net 内置星表 (从粗到细)
AstrometryIndexFiles = {
    "4208": "/usr/share/astrometry/index-4208-*.fits",  # 0-1 deg
    "4207": "/usr/share/astrometry/index-4207-*.fits",  # 1-2 deg
    "4206": "/usr/share/astrometry/index-4206-*.fits",  # 2-3 deg
    "4205": "/usr/share/astrometry/index-4205-*.fits",  # 3-4 deg
    "4204": "/usr/share/astrometry/index-4204-*.fits",  # 4-7 deg
    "4203": "/usr/share/astrometry/index-4203-*.fits",  # 7-15 deg
}


class AstrometrySolver:
    """
    astrometry.net 图像求解器封装
    
    使用 astrometry-engine 对 FITS 图像进行 plate-solving，
    确定图像的天球坐标 (RA/Dec) 和视场参数
    """
    
    def __init__(
        self,
        index_dir: str = "/usr/share/astrometry",
        work_dir: Optional[str] = None,
        cpu_njobs: int = -1
    ):
        """
        Args:
            index_dir: astrometry.net 星表索引目录
            work_dir: 临时工作目录
            cpu_njobs: CPU核心数 (-1=全部)
        """
        self.index_dir = index_dir
        self.work_dir = work_dir or tempfile.mkdtemp(prefix="astrometry_")
        self.cpu_njobs = cpu_njobs
        
        # 检测astrometry-engine是否可用
        self.available = self._check_engine()
        
    def _check_engine(self) -> bool:
        """检查astrometry-engine是否安装"""
        try:
            result = subprocess.run(
                ["astrometry-engine", "--version"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip().split('\n')[0] if result.stdout else "unknown"
                logger.info(f"astrometry-engine 可用: {version}")
                return True
            return False
        except FileNotFoundError:
            logger.info("[INSTALL REQUIRED] astrometry-engine 未找到")
            logger.info("  安装命令: sudo apt-get install astrometry-net")
            logger.info("  或访问: https://github.com/dstndstn/astrometry.net")
            return False
        except (subprocess.SubprocessError):
            return False
    
    def _get_index_files(self) -> List[str]:
        """获取可用的星表索引文件"""
        indices = []
        if os.path.exists(self.index_dir):
            for f in os.listdir(self.index_dir):
                if f.startswith("index-") and f.endswith(".fits"):
                    indices.append(os.path.join(self.index_dir, f))
        return sorted(indices)
    
    def solve(
        self,
        image_path: str,
        ra_hint: Optional[float] = None,
        dec_hint: Optional[float] = None,
        radius_hint: float = 5.0,
        pixel_scale: Optional[float] = None,
        downsample: int = 2,
        timeout: int = 300
    ) -> Optional[Dict[str, Any]]:
        """
        对FITS图像进行Plate-Solving
        
        Args:
            image_path: FITS图像路径
            ra_hint: 粗略RA坐标提示 (度)
            dec_hint: 粗略Dec坐标提示 (度)
            radius_hint: 搜索半径 (度)
            pixel_scale: 像素分辨率 (arcsec/pixel)，如果已知
            downsample: 下采样倍数 (加速匹配)
            timeout: 超时时间 (秒)
            
        Returns:
            求解结果字典，包含 WCS 参数，或 None
        """
        if not self.available:
            logger.info("astrometry-engine 不可用，使用 astropy.wcs 模拟")
            return self._mock_solve(image_path)
        
        # 构建求解命令
        cmd = [
            "astrometry-engine",
            "--seedxy", "100", "100",  # 从图像中心开始
            "--downsample", str(downsample),
            "--no-verify",  # 不验证
            "--no-plots",
            "--overwrite",
            "--wcs", os.path.join(self.work_dir, "result.wcs"),
        ]
        
        # 添加RA/Dec提示
        if ra_hint is not None and dec_hint is not None:
            cmd.extend([
                "--ra", str(ra_hint),
                "--dec", str(dec_hint),
                "--radius", str(radius_hint)
            ])
        
        # 添加像素比例
        if pixel_scale is not None:
            cmd.extend([
                "--scale-low", str(pixel_scale * 0.9),
                "--scale-high", str(pixel_scale * 1.1),
                "--scale-units", "arcsecperpix"
            ])
        else:
            cmd.append("--scale-units", "degwidth")
        
        # 图像路径
        cmd.append(image_path)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.work_dir
            )
            
            if result.returncode == 0:
                return self._parse_wcs_result()
            else:
                logger.info(f"求解失败: {result.stderr}")
                return self._mock_solve(image_path)
                
        except subprocess.TimeoutExpired:
            logger.info(f"求解超时 ({timeout}s)")
            return None
        except Exception as e:
            logger.info(f"求解异常: {e}")
            return None
    
    def _parse_wcs_result(self) -> Optional[Dict[str, Any]]:
        """解析WCS结果文件"""
        wcs_path = os.path.join(self.work_dir, "result.wcs")
        if not os.path.exists(wcs_path):
            return None
            
        if not HAS_ASTROPY:
            return {"wcs_file": wcs_path, "status": "solved"}
            
        try:
            with open(wcs_path, "r") as f:
                wcs_data = f.read()
            
            # 简单解析WCS头
            result = {"status": "solved", "wcs_file": wcs_path}
            
            for line in wcs_data.split("\n"):
                if "CRVAL1" in line:
                    result["ra"] = float(line.split("=")[1].split()[0])
                elif "CRVAL2" in line:
                    result["dec"] = float(line.split("=")[1].split()[0])
                elif "CD1_1" in line:
                    result["cd"] = [
                        float(line.split("=")[1].split()[0])
                    ]
                    
            return result
        except Exception as e:
            return {"wcs_file": wcs_path, "status": "solved", "parse_error": str(e)}
    
    def _mock_solve(self, image_path: str) -> Optional[Dict[str, Any]]:
        """当astrometry不可用时，使用astropy模拟WCS"""
        if not HAS_ASTROPY:
            logger.info("astropy也未安装，无法进行WCS求解")
            return None
            
        try:
            with fits.open(image_path) as hdul:
                header = hdul[0].header
                
            # 尝试读取已有的WCS
            try:
                wcs = wcsmod.WCS(header)
                return {
                    "status": "from_header",
                    "ra": float(wcs.wcs.crval[0]),
                    "dec": float(wcs.wcs.crval[1]),
                    "wcs": wcs
                }
            except Exception:
                logger.info("无法从FITS头读取WCS，且astrometry.net不可用。请安装 astrometry.net 进行板解。")
                return None
        except Exception as e:
            logger.info(f"FITS读取失败: {e}")
            return None
    
    def solve_from_image_data(
        self,
        image_data: np.ndarray,
        header: Optional[Dict] = None,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        从numpy数组直接求解（写入临时FITS）
        """
        if not HAS_ASTROPY:
            return None
            
        with tempfile.NamedTemporaryFile(suffix=".fits", delete=False) as f:
            temp_path = f.name
            
        try:
            if header:
                hdu = fits.PrimaryHDU(image_data, header=fits.Header(header))
            else:
                hdu = fits.PrimaryHDU(image_data)
            hdu.writeto(temp_path, overwrite=True)
            return self.solve(temp_path, **kwargs)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    def cleanup(self):
        """清理临时文件"""
        if os.path.exists(self.work_dir):
            shutil.rmtree(self.work_dir, ignore_errors=True)


if __name__ == "__main__":
    solver = AstrometrySolver()
    logger.info(f"astrometry-engine 可用: {solver.available}")
    logger.info(f"星表索引: {len(solver._get_index_files())} 个")
