"""Module entry point; no background process or network service."""
from .workbench import main

raise SystemExit(main())
