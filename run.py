#!/usr/bin/env python3
"""
在线考试系统 - 启动脚本
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8032,
        reload=True
    )
