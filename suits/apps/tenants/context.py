# apps/tenants/context.py

import threading

_thread_locals = threading.local()

def set_current_tenant(tenant):
    _thread_locals.current_tenant = tenant

def get_current_tenant():
    return getattr(_thread_locals, "current_tenant", None)

def clear_current_tenant():
    if hasattr(_thread_locals, "current_tenant"):
        del _thread_locals.current_tenant