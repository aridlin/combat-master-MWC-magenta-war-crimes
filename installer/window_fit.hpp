#pragma once
#include <algorithm>

namespace mwc_window {
struct Rect { int x,y,w,h; };
// All coordinates are native pixels, including monitors left/above the primary.
inline Rect fit(Rect work,int width,int height,int top=0,int bottom=0,int side=0) {
    const int margin=std::min(16,std::max(0,std::min(work.w,work.h)/8));
    int w=std::max(1,std::min(width,work.w-2*margin-2*side));
    int h=std::max(1,std::min(height,work.h-2*margin-top-bottom));
    return {work.x+(work.w-w)/2,work.y+margin+top,w,h};
}

inline Rect work_area() {
#ifdef _WIN32
    SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
    POINT cursor{};GetCursorPos(&cursor);
    MONITORINFO info{sizeof(info)};
    if(GetMonitorInfoW(MonitorFromPoint(cursor,MONITOR_DEFAULTTONEAREST),&info)) {
        auto r=info.rcWork;return {r.left,r.top,r.right-r.left,r.bottom-r.top};
    }
    return {0,0,GetSystemMetrics(SM_CXSCREEN),GetSystemMetrics(SM_CYSCREEN)};
#else
    auto* dpy=XOpenDisplay(nullptr);if(!dpy)return {0,0,1024,768};
    Rect work{0,0,DisplayWidth(dpy,DefaultScreen(dpy)),DisplayHeight(dpy,DefaultScreen(dpy))};
#if __has_include(<X11/extensions/Xinerama.h>)
    static void* lib=dlopen("libXinerama.so.1",RTLD_LAZY|RTLD_LOCAL);
    if(lib) {
        using Screens=XineramaScreenInfo*(*)(Display*,int*);using Active=Bool(*)(Display*);
        auto screens=(Screens)dlsym(lib,"XineramaQueryScreens");auto active=(Active)dlsym(lib,"XineramaIsActive");
        Window root,child;int rx=0,ry=0,wx,wy;unsigned mask;
        XQueryPointer(dpy,DefaultRootWindow(dpy),&root,&child,&rx,&ry,&wx,&wy,&mask);
        int count=0;auto* monitors=screens&&active&&active(dpy)?screens(dpy,&count):nullptr;
        for(int n=0;monitors&&n<count;++n){auto m=monitors[n];
            if(rx>=m.x_org&&ry>=m.y_org&&rx<m.x_org+m.width&&ry<m.y_org+m.height)
                work={m.x_org,m.y_org,m.width,m.height};
        }
        if(monitors)XFree(monitors);
    }
#endif
    auto cardinal=[&](const char* name,long offset,long count){
        std::vector<unsigned long> values;Atom type;int format;unsigned long n,left;unsigned char* data=nullptr;
        if(XGetWindowProperty(dpy,DefaultRootWindow(dpy),XInternAtom(dpy,name,False),offset,count,False,XA_CARDINAL,&type,&format,&n,&left,&data)==0&&data&&format==32)
            values.assign((unsigned long*)data,(unsigned long*)data+n);
        if(data)XFree(data);return values;
    };
    auto desktop=cardinal("_NET_CURRENT_DESKTOP",0,1);
    auto area=cardinal("_NET_WORKAREA",desktop.empty()?0:desktop[0]*4,4);
    if(area.size()==4){int x=std::max(work.x,int(area[0])),y=std::max(work.y,int(area[1]));
        int right=std::min(work.x+work.w,int(area[0])+int(area[2])),bottom=std::min(work.y+work.h,int(area[1])+int(area[3]));
        if(right>x&&bottom>y)work={x,y,right-x,bottom-y};
    }
    XCloseDisplay(dpy);return work;
#endif
}

inline Rect prepare(ft::Config& config,bool& maximize) {
    auto work=work_area();
#ifdef _WIN32
    float scale=GetDpiForSystem()/96.f;
    auto target=fit(work,int(config.width*scale),int(config.height*scale),int(48*scale),int(12*scale),int(12*scale));
    maximize=target.w<int(config.width*scale)||target.h<int(config.height*scale);
    config.width=std::max(1,int(target.w/scale));config.height=std::max(1,int(target.h/scale));
#else
    // X11 dimensions are pixels; leave room for the window manager's decoration.
    auto target=fit(work,config.width,config.height,48,12,8);
    maximize=target.w<config.width||target.h<config.height;
    config.width=target.w;config.height=target.h;
#endif
    config.center_window=false;return work;
}

inline void place(Rect work,bool maximize) {
#ifdef _WIN32
    auto window=(HWND)ft::native_window();RECT r{};GetWindowRect(window,&r);
    auto target=fit(work,r.right-r.left,r.bottom-r.top);
    SetWindowPos(window,nullptr,target.x,target.y,target.w,target.h,SWP_NOZORDER|SWP_NOACTIVATE);
    if(maximize)ShowWindow(window,SW_MAXIMIZE);
#else
    auto& p=ftui::internal::g_platform;
    auto target=fit(work,p.width,p.height,48,12,8);
    ft::set_window_position(target.x,target.y);
    if(maximize) {
        // Let the desktop account for the real title bar, panels and scaling.
        // Set the initial property as well as sending the mapped-window request:
        // FT maps the window before returning, so the WM may not have managed it yet.
        auto* dpy=p.display;auto window=p.window;
        Atom state=XInternAtom(dpy,"_NET_WM_STATE",False);
        Atom states[]={XInternAtom(dpy,"_NET_WM_STATE_MAXIMIZED_VERT",False),
                       XInternAtom(dpy,"_NET_WM_STATE_MAXIMIZED_HORZ",False)};
        XChangeProperty(dpy,window,state,XA_ATOM,32,PropModeReplace,
                        reinterpret_cast<unsigned char*>(states),2);
        XEvent event{};event.xclient.type=ClientMessage;event.xclient.window=window;
        event.xclient.message_type=state;event.xclient.format=32;
        event.xclient.data.l[0]=1; // _NET_WM_STATE_ADD
        event.xclient.data.l[1]=states[0];event.xclient.data.l[2]=states[1];
        event.xclient.data.l[3]=1; // Application request
        XSendEvent(dpy,DefaultRootWindow(dpy),False,
                   SubstructureRedirectMask|SubstructureNotifyMask,&event);
        XFlush(dpy);
    }
#endif
}
}
