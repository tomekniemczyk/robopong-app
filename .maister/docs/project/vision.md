# Project Vision

## Overview
AcePad is a ping pong robot controller application that replaces the proprietary Newgy software for the Donic Robopong 3050XL, providing full control over robot parameters through a modern web interface.

## Current State
- **Age**: ~18 weeks of active development (243 commits)
- **Status**: Active development, production-deployed
- **Users**: Table tennis players and coaches using Robopong 3050XL
- **Tech Stack**: Python 3.11 (FastAPI) + Vue 3 (CDN) + SQLite + BLE/USB

## Purpose
The original Newgy software for Robopong 3050XL is limited and proprietary. AcePad provides:
- Full parameter control over the robot (speed, spin, oscillation, height, rotation)
- Multi-device connectivity (BLE + USB FTDI) with simulation fallback
- Structured training system with drills, exercises, and training programs
- Multi-user session management (controller/observer roles with takeover)
- Player profiles with training history, recordings, and statistics
- Video recording of training sessions with comparison tools
- Mobile-first PWA accessible from any device on the network

## Goals (Next 6-12 Months)
- Stabilize existing features and improve code quality
- Harden BLE/USB connectivity and reconnection logic
- Polish training flow UX based on real-world usage feedback
- Expand drill library based on coaching methodology

## Evolution
The project started from reverse engineering the Robopong 3050XL communication protocol (documented in `/re/`). Protocol understanding progressed through Android, Windows, and iOS app analysis, establishing a complete picture of the robot's capabilities. The application evolved from basic robot control to a comprehensive training platform with player management, session recording, and structured drill programs.
