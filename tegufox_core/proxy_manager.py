#!/usr/bin/env python3
"""
Tegufox Proxy Manager

Manages proxy pool with CRUD operations, bulk import, and testing.

Author: Tegufox Browser Toolkit
Date: April 23, 2026
License: MIT
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Text,
    DateTime,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

Base = declarative_base()


class ProxyPool(Base):
    """Proxy pool table"""

    __tablename__ = "proxy_pool"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    username = Column(String(255))
    password = Column(String(255))
    protocol = Column(String(20), default="http")  # http, https, socks5
    status = Column(String(20), default="inactive")  # active, inactive, failed
    last_checked = Column(DateTime)
    last_ip = Column(String(50))
    created = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict"""
        return {
            "name": self.name,
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": self.password,
            "protocol": self.protocol,
            "status": self.status,
            "last_checked": self.last_checked.strftime("%Y-%m-%d %H:%M:%S") if self.last_checked else None,
            "last_ip": self.last_ip,
            "created": self.created.strftime("%Y-%m-%d %H:%M:%S") if self.created else None,
            "notes": self.notes,
        }


def parse_proxy_line(line: str) -> Optional[Dict[str, Any]]:
    """
    Parse proxy string to dict
    
    Supports:
    - ip:port:user:pass
    - user:pass@ip:port
    - ip:port (no auth)
    
    Returns:
        Dict with host, port, username, password or None if invalid
    """
    line = line.strip()
    if not line:
        return None
    
    # Format: user:pass@ip:port
    match = re.match(r'^([^:@]+):([^:@]+)@([^:]+):(\d+)$', line)
    if match:
        username, password, host, port = match.groups()
        return {
            "host": host,
            "port": int(port),
            "username": username,
            "password": password,
        }
    
    # Format: ip:port:user:pass
    parts = line.split(':')
    if len(parts) == 4:
        host, port, username, password = parts
        try:
            return {
                "host": host,
                "port": int(port),
                "username": username,
                "password": password,
            }
        except ValueError:
            return None
    
    # Format: ip:port (no auth)
    if len(parts) == 2:
        host, port = parts
        try:
            return {
                "host": host,
                "port": int(port),
                "username": None,
                "password": None,
            }
        except ValueError:
            return None
    
    return None


def format_proxy_url(proxy_dict: Dict[str, Any]) -> str:
    """
    Convert proxy dict to URL format
    
    Args:
        proxy_dict: Dict with host, port, username, password, protocol
    
    Returns:
        Proxy URL string (e.g., http://user:pass@host:port)
    """
    protocol = proxy_dict.get("protocol", "http")
    host = proxy_dict["host"]
    port = proxy_dict["port"]
    username = proxy_dict.get("username")
    password = proxy_dict.get("password")
    
    if username and password:
        return f"{protocol}://{username}:{password}@{host}:{port}"
    return f"{protocol}://{host}:{port}"


class ProxyManager:
    """Proxy pool manager"""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize proxy database
        
        Args:
            db_path: Path to SQLite database (default: tegufox_core/proxies.db)
        """
        if db_path is None:
            db_path = str(Path(__file__).parent / "proxies.db")
        
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def get_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()

    def create(
        self,
        name: str,
        host: str,
        port: int,
        username: Optional[str] = None,
        password: Optional[str] = None,
        protocol: str = "http",
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create new proxy
        
        Args:
            name: Unique proxy name
            host: IP address or hostname
            port: Port number
            username: Optional username
            password: Optional password
            protocol: Protocol (http, https, socks5)
            notes: Optional notes
        
        Returns:
            Created proxy dict
        
        Raises:
            ValueError: If proxy name already exists
        """
        session = self.get_session()
        try:
            # Check if name exists
            existing = session.query(ProxyPool).filter_by(name=name).first()
            if existing:
                raise ValueError(f"Proxy '{name}' already exists")
            
            proxy = ProxyPool(
                name=name,
                host=host,
                port=port,
                username=username,
                password=password,
                protocol=protocol,
                notes=notes,
            )
            session.add(proxy)
            session.commit()
            return proxy.to_dict()
        finally:
            session.close()

    def bulk_import(self, proxy_list: List[str], format: str = "auto") -> Tuple[int, List[str]]:
        """
        Import multiple proxies from list
        
        Args:
            proxy_list: List of proxy strings
            format: Format hint ('auto', 'colon', 'at') - currently auto-detects
        
        Returns:
            Tuple of (success_count, error_messages)
        """
        session = self.get_session()
        success_count = 0
        errors = []
        
        try:
            # Get existing proxy count for naming
            existing_count = session.query(ProxyPool).count()
            counter = existing_count + 1
            
            for line in proxy_list:
                parsed = parse_proxy_line(line)
                if not parsed:
                    errors.append(f"Invalid format: {line}")
                    continue
                
                # Generate unique name
                name = f"proxy_{counter}"
                while session.query(ProxyPool).filter_by(name=name).first():
                    counter += 1
                    name = f"proxy_{counter}"
                
                proxy = ProxyPool(
                    name=name,
                    host=parsed["host"],
                    port=parsed["port"],
                    username=parsed.get("username"),
                    password=parsed.get("password"),
                )
                session.add(proxy)
                success_count += 1
                counter += 1
            
            session.commit()
        except Exception as e:
            session.rollback()
            errors.append(f"Database error: {str(e)}")
        finally:
            session.close()
        
        return success_count, errors

    def update(self, name: str, **kwargs) -> Dict[str, Any]:
        """
        Update proxy fields
        
        Args:
            name: Proxy name
            **kwargs: Fields to update (host, port, username, password, protocol, notes, status)
        
        Returns:
            Updated proxy dict
        
        Raises:
            ValueError: If proxy not found
        """
        session = self.get_session()
        try:
            proxy = session.query(ProxyPool).filter_by(name=name).first()
            if not proxy:
                raise ValueError(f"Proxy '{name}' not found")
            
            # Update allowed fields
            allowed_fields = ["host", "port", "username", "password", "protocol", "notes", "status"]
            for key, value in kwargs.items():
                if key in allowed_fields:
                    setattr(proxy, key, value)
            
            session.commit()
            return proxy.to_dict()
        finally:
            session.close()

    def delete(self, name: str) -> None:
        """
        Delete proxy
        
        Args:
            name: Proxy name
        
        Raises:
            ValueError: If proxy not found
        """
        session = self.get_session()
        try:
            proxy = session.query(ProxyPool).filter_by(name=name).first()
            if not proxy:
                raise ValueError(f"Proxy '{name}' not found")
            
            session.delete(proxy)
            session.commit()
        finally:
            session.close()

    def delete_multiple(self, names: List[str]) -> Tuple[int, List[str]]:
        """
        Delete multiple proxies
        
        Args:
            names: List of proxy names
        
        Returns:
            Tuple of (success_count, error_messages)
        """
        session = self.get_session()
        success_count = 0
        errors = []
        
        try:
            for name in names:
                proxy = session.query(ProxyPool).filter_by(name=name).first()
                if proxy:
                    session.delete(proxy)
                    success_count += 1
                else:
                    errors.append(f"Proxy '{name}' not found")
            
            session.commit()
        except Exception as e:
            session.rollback()
            errors.append(f"Database error: {str(e)}")
        finally:
            session.close()
        
        return success_count, errors

    def list(self) -> List[str]:
        """
        List all proxy names
        
        Returns:
            List of proxy names
        """
        session = self.get_session()
        try:
            proxies = session.query(ProxyPool.name).all()
            return [p.name for p in proxies]
        finally:
            session.close()

    def load(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Load proxy by name
        
        Args:
            name: Proxy name
        
        Returns:
            Proxy dict or None if not found
        """
        session = self.get_session()
        try:
            proxy = session.query(ProxyPool).filter_by(name=name).first()
            return proxy.to_dict() if proxy else None
        finally:
            session.close()

    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search proxies by name or host
        
        Args:
            query: Search query
        
        Returns:
            List of matching proxy dicts
        """
        session = self.get_session()
        try:
            query_pattern = f"%{query}%"
            proxies = session.query(ProxyPool).filter(
                (ProxyPool.name.like(query_pattern)) | (ProxyPool.host.like(query_pattern))
            ).all()
            return [p.to_dict() for p in proxies]
        finally:
            session.close()

    def test_proxy(self, name: str, timeout: int = 10) -> Dict[str, Any]:
        """
        Test proxy by fetching external IP
        
        Args:
            name: Proxy name
            timeout: Request timeout in seconds
        
        Returns:
            Dict with success, ip, error, response_time
        """
        session = self.get_session()
        try:
            proxy = session.query(ProxyPool).filter_by(name=name).first()
            if not proxy:
                return {"success": False, "error": "Proxy not found", "ip": None}
            
            # Build proxy URL
            proxy_url = format_proxy_url(proxy.to_dict())
            
            # Test with httpx
            try:
                import httpx
                import time
                
                start_time = time.time()
                # httpx uses proxy parameter
                with httpx.Client(proxy=proxy_url, timeout=timeout) as client:
                    response = client.get("https://api.ipify.org?format=text")
                    response.raise_for_status()
                    ip = response.text.strip()
                    response_time = time.time() - start_time
                
                # Update proxy status
                proxy.status = "active"
                proxy.last_checked = datetime.utcnow()
                proxy.last_ip = ip
                session.commit()
                
                return {
                    "success": True,
                    "ip": ip,
                    "error": None,
                    "response_time": round(response_time, 2),
                }
            except Exception as e:
                # Update proxy status to failed
                proxy.status = "failed"
                proxy.last_checked = datetime.utcnow()
                session.commit()
                
                return {
                    "success": False,
                    "ip": None,
                    "error": str(e),
                }
        finally:
            session.close()
