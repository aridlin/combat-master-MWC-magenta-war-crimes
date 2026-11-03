#define FT_IMPLEMENTATION
#include "vendor/ft.hpp"
#include <filesystem>
#include <fstream>
#include <thread>
#include <atomic>
#include <sstream>
#include <vector>
#include <chrono>
#ifndef _WIN32
#include <sys/wait.h>
#include <unistd.h>
#include <fcntl.h>
#endif
#include "catalog.generated.hpp"
namespace fs=std::filesystem;
static std::atomic<bool> busy{false};static std::atomic<int> result{-1};
static std::string escape(const std::string&s){std::string o;for(unsigned char c:s){if(c=='"'||c=='\\'){o+='\\';o+=c;}else if(c=='\n')o+="\\n";else if(c=='\r')o+="\\r";else if(c=='\t')o+="\\t";else if(c<32)o+=' ';else o+=c;}return o;}
#ifdef _WIN32
static std::wstring wide(const std::string&s){int n=MultiByteToWideChar(CP_UTF8,0,s.c_str(),-1,nullptr,0);std::wstring w(n,L'\0');MultiByteToWideChar(CP_UTF8,0,s.c_str(),-1,w.data(),n);w.pop_back();return w;}
static std::wstring quote(const std::wstring&s){std::wstring o=L"\"";int slash=0;for(auto c:s){if(c==L'\\'){++slash;continue;}if(c==L'"')o.append(slash*2+1,L'\\');else o.append(slash,L'\\');slash=0;o+=c;}o.append(slash*2,L'\\');return o+L'"';}
#endif
static int run(const std::vector<std::string>&args,const fs::path&log){
#ifdef _WIN32
 SECURITY_ATTRIBUTES sa{sizeof(sa),nullptr,TRUE};HANDLE h=CreateFileW(log.c_str(),GENERIC_WRITE,FILE_SHARE_READ|FILE_SHARE_WRITE,&sa,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);if(h==INVALID_HANDLE_VALUE)return 126;
 std::wstring cmd;for(auto&s:args){if(!cmd.empty())cmd+=L' ';cmd+=quote(wide(s));}STARTUPINFOW si{};si.cb=sizeof(si);si.dwFlags=STARTF_USESTDHANDLES;si.hStdOutput=si.hStdError=h;si.hStdInput=GetStdHandle(STD_INPUT_HANDLE);PROCESS_INFORMATION pi{};
 BOOL ok=CreateProcessW(nullptr,cmd.data(),nullptr,nullptr,TRUE,CREATE_NO_WINDOW,nullptr,nullptr,&si,&pi);CloseHandle(h);if(!ok)return 127;WaitForSingleObject(pi.hProcess,INFINITE);DWORD code;GetExitCodeProcess(pi.hProcess,&code);CloseHandle(pi.hProcess);CloseHandle(pi.hThread);return int(code);
#else
 pid_t pid=fork();if(pid<0)return 126;if(pid==0){int fd=open(log.c_str(),O_WRONLY|O_CREAT|O_TRUNC,0600);if(fd<0)_exit(126);dup2(fd,1);dup2(fd,2);close(fd);std::vector<char*>v;for(auto&s:args)v.push_back(const_cast<char*>(s.c_str()));v.push_back(nullptr);execvp(v[0],v.data());_exit(127);}int status=0;while(waitpid(pid,&status,0)<0){if(errno!=EINTR)return 126;}return WIFEXITED(status)?WEXITSTATUS(status):128;
#endif
}
static std::string read(const fs::path&p){std::ifstream f(p,std::ios::binary);return {std::istreambuf_iterator<char>(f),{}};}
int main(int argc,char**argv){
 fs::path home=fs::absolute(fs::u8path(argv[0])).parent_path();
#ifdef _WIN32
 wchar_t exe[32768];GetModuleFileNameW(nullptr,exe,32768);home=fs::path(exe).parent_path();
#else
 std::error_code ec;auto exe=fs::read_symlink("/proc/self/exe",ec);if(!ec)home=exe.parent_path();
#endif
 fs::path state;
 if(argc>2&&std::string(argv[1])=="--state")state=fs::absolute(fs::u8path(argv[2]));
 else {
#ifdef _WIN32
 const char*base=getenv("LOCALAPPDATA");state=fs::u8path(base?base:".")/"CombatMasterMWC";
#else
 const char*base=getenv("XDG_DATA_HOME");const char*user=getenv("HOME");state=base?fs::u8path(base)/"combat-master-mwc":fs::u8path(user?user:".")/".local/share/combat-master-mwc";
#endif
 }
 fs::create_directories(state);std::vector<std::string>backend;
#ifdef _WIN32
 backend={(home/"runtime/python.exe").u8string(),(home/"source/installer/backend.py").u8string()};
#else
 if(fs::exists(home/"backend/mwc-backend"))backend={(home/"backend/mwc-backend").u8string()};else backend={"python3",(home/"backend.py").u8string()};
#endif
 auto statusargs=backend;statusargs.insert(statusargs.end(),{"--status",(state/"discovered.txt").u8string()});run(statusargs,state/"discovery.log");
 char game[4096]={},addon[4096]={},tf2[4096]={};auto bundled=home/"addons/M1A0-Cat-Gun.bin";if(fs::exists(bundled))snprintf(addon,sizeof(addon),"%s",bundled.u8string().c_str());auto detected=read(state/"discovered.txt");snprintf(game,sizeof(game),"%s",detected.c_str());snprintf(tf2,sizeof(tf2),"%s",read(state/"tf2.txt").c_str());
 auto saved=read(state/"selected.txt");for(auto&m:mods)m.selected=saved.find(m.id+"\n")!=std::string::npos||saved==m.id;
 std::istringstream choices(read(state/"operator-plan.tsv"));std::string line;while(std::getline(choices,line)){auto split=line.find('\t');if(split==std::string::npos)continue;for(auto&t:operator_targets)if(t.id==line.substr(0,split))for(size_t n=0;n<operator_models.size();++n)if(operator_models[n].id==line.substr(split+1))t.choice=int(n);}
 bool native_magenta=false;for(auto&m:mods)if(m.id=="players")native_magenta=m.selected;
 for(auto&m:operator_models)m.magenta=m.id.rfind("tf2_",0)==0||m.id=="titanfall_pilot";
 std::istringstream colors(read(state/"operator-appearance.tsv"));while(std::getline(colors,line)){auto split=line.find('\t');if(split==std::string::npos)continue;bool enabled=line.substr(split+1)=="1";if(line.substr(0,split)=="game_customs")native_magenta=enabled;for(auto&m:operator_models)if(m.id==line.substr(0,split))m.magenta=enabled;}
 std::vector<const char*>operator_labels;for(auto&m:operator_models)operator_labels.push_back(m.title.c_str());
 std::string capture;int tab=0;for(int n=1;n+1<argc;++n){if(std::string(argv[n])=="--capture")capture=argv[n+1];if(std::string(argv[n])=="--tab")tab=std::max(0,std::min(3,atoi(argv[n+1])));}
 bool authorized=false;std::thread worker;std::string job_action;std::string notice="Choose mods independently. Originals are backed up before installation.";
 ft::Config c;c.mode=ft::Mode::Gui;c.title="Combat Master MWC - Magenta War Crimes";c.width=1180;c.height=1400;c.window_opacity=1;c.enable_effects=false;c.fps_limit=30;
 if(!ft::create_window(c))return 2;
 auto seal=ft::load_image((home/"branding/fishguy-sticker.png").u8string().c_str());
 auto reload_previews=[&]{
  for(auto&m:mods){if(m.image)ft::free_image(m.image);auto local=state/"previews"/(m.id+".png");bool imported=fs::exists(local);m.image=ft::load_image((imported?local:home/fs::u8path(m.thumbnail)).u8string().c_str());if(imported){m.thumb_w=640;m.thumb_h=480;}}
  for(auto&m:operator_models){if(m.image)ft::free_image(m.image);m.image=nullptr;auto local=state/"previews"/(m.id+".png");if(fs::exists(local)){m.image=ft::load_image(local.u8string().c_str());m.thumb_w=480;m.thumb_h=600;}else if(!m.thumbnail.empty())m.image=ft::load_image((home/fs::u8path(m.thumbnail)).u8string().c_str());}
 };reload_previews();
 auto write_appearance=[&](std::ostream&f){f<<",\"operator_appearance\":{\"game_customs_magenta\":"<<(native_magenta?"true":"false")<<",\"model_magenta\":{";bool first=true;for(auto&m:operator_models)if(m.id!="original"){if(!first)f<<',';first=false;f<<'"'<<m.id<<"\":"<<(m.magenta?"true":"false");}f<<"}}";};
 auto start=[&](const char*action){
  if(busy)return;if(worker.joinable())worker.join();job_action=action;
  std::ofstream f(state/"request.json");f<<"{\"action\":\""<<action<<"\",\"game\":\""<<escape(game)<<"\",\"addon\":\""<<escape(addon)<<"\",\"state\":\""<<escape(state.u8string())<<"\",\"tf2\":\""<<escape(tf2)<<"\",\"offline_authorized\":"<<(authorized?"true":"false")<<",\"selected\":[";bool first=true;for(auto&m:mods)if(m.selected){if(!first)f<<',';first=false;f<<'"'<<m.id<<'"';}f<<"],\"supported_mods\":[";first=true;for(auto&m:mods){if(!first)f<<',';first=false;f<<'"'<<m.id<<'"';}f<<"],\"operator_assignments\":{";first=true;for(auto&t:operator_targets)if(t.choice){if(!first)f<<',';first=false;f<<'"'<<t.id<<"\":\""<<operator_models[t.choice].id<<'"';}f<<"}";write_appearance(f);f<<"}";f.close();
  auto args=backend;args.insert(args.end(),{"--request",(state/"request.json").u8string()});busy=true;result=-1;notice=job_action=="save_operators"?"Saving operator choices. Game files stay unchanged.":"Working. Building and verifying bundles before installation...";worker=std::thread([&,args]{result=run(args,state/"install.log");busy=false;});
 };
 while(ft::pump()){
  if(!busy&&result>=0){if(result==0&&job_action=="preview_tf2")reload_previews();notice=result==0?(job_action=="preview_tf2"?"Local TF2 previews imported. Game files unchanged.":job_action=="save_operators"?"Operator choices saved. Use Apply selected mods to build and install available models.":job_action=="restore"?"Complete. Original bundles restored and hashes verified.":"Complete. Selected mods installed and hashes verified."):"Could not finish. Read the log below; previous installed state was preserved or recovered.";result=-1;}
  ft::begin();
  ft::row({.13f,.87f},[&]{ft::content([&]{if(seal)ft::image(seal,128,128);});ft::content([&]{ft::text("COMBAT MASTER  /  MWC");ft::text("Magenta War Crimes - choose your own chaos");ft::text("Individual mods | verified backups | restore originals");});});
  ft::input("Combat Master game folder (blank = Steam detection)",game,sizeof(game));
  ft::input("M1A0 workshop .bin / .gma (needed only for Lynx / cat sounds)",addon,sizeof(addon));
  if(ft::button("Choose local M1A0 archive")){auto p=ft::open_file_dialog("M1A0 Cat Gun archive",nullptr,0);if(!p.empty())snprintf(addon,sizeof(addon),"%s",p.c_str());}
  const char*tabs[]={"Weapon models","Textures","Extras","Operators"};ft::tabs(tabs,4,&tab);
  if(tab==3){
   ft::text_wrapped("Choose each operator's model. Previews show source colors; Magenta applies at install. In-game tests remain pending.");
   ft::input("Local TF2 folder for mercenary models (blank = Steam detection)",tf2,sizeof(tf2));
   if(busy)ft::begin_disabled();if(ft::button("Import TF2 previews (game files unchanged)"))start("preview_tf2");if(busy)ft::end_disabled();
   if(busy)ft::begin_disabled();ft::checkbox("Magenta for unmodified in-game operator models",&native_magenta);if(busy)ft::end_disabled();
   ft::scroll_area("Operator assignments",490,[&]{for(auto&t:operator_targets){ft::row({.22f,.48f,.30f},[&]{ft::content([&]{ft::text(t.title.c_str());});ft::content([&]{if(busy)ft::begin_disabled();ft::dropdown(("Model##"+t.id).c_str(),operator_labels.data(),int(operator_labels.size()),&t.choice);ft::text_wrapped(operator_models[t.choice].status.c_str());if(busy)ft::end_disabled();});ft::content([&]{auto&m=operator_models[t.choice];if(t.choice){if(busy)ft::begin_disabled();ft::checkbox(("Magenta##color_"+t.id).c_str(),&m.magenta);if(busy)ft::end_disabled();}if(m.image){float fit=std::min(225.f/m.thumb_w,145.f/m.thumb_h);ft::image(m.image,m.thumb_w*fit,m.thumb_h*fit);}});});ft::separator();}});
   if(busy)ft::begin_disabled();ft::row(2,[&]{if(ft::button("Save operator choices and colors"))start("save_operators");if(ft::button("Use game models for all operators"))for(auto&t:operator_targets)t.choice=0;});if(busy)ft::end_disabled();
  }else ft::scroll_area("Mod catalogue",600,[&]{std::vector<Mod*>shown;for(auto&m:mods)if(m.group==std::string(tab==0?"Models":tab==1?"Textures":"Extras"))shown.push_back(&m);for(size_t n=0;n<shown.size();n+=3){ft::row(3,[&]{for(size_t i=n;i<std::min(n+3,shown.size());++i){auto&m=*shown[i];ft::content([&]{if(busy)ft::begin_disabled();ft::checkbox(m.title.c_str(),&m.selected);if(m.image){float fit=std::min(290.f/m.thumb_w,203.f/m.thumb_h);ft::image(m.image,m.thumb_w*fit,m.thumb_h*fit);}ft::text_wrapped(m.kind.c_str());ft::text_wrapped(m.description.c_str());ft::separator();if(busy)ft::end_disabled();});}});}});
  if(busy)ft::begin_disabled();ft::checkbox("I will use these mods offline or in an explicitly authorized environment",&authorized);
  ft::row(2,[&]{if(!authorized)ft::begin_disabled();if(ft::button("Apply selected mods",ft::ColorRole::Accent))start("apply");if(!authorized)ft::end_disabled();if(ft::button("Restore all originals"))start("restore");});if(busy)ft::end_disabled();
  ft::text_wrapped(notice.c_str());auto logs=read(state/"install.log");if(logs.size()>5000)logs=logs.substr(logs.size()-5000);ft::code_view("Build / install log",logs.c_str(),5);if(busy)ft::request_redraw();ft::end();
#ifndef _WIN32
  if(!capture.empty()){cairo_surface_write_to_png(cairo_get_target(ftui::internal::g_renderer.cr),capture.c_str());break;}
#endif
 }
 if(worker.joinable())worker.join();for(auto&m:mods)if(m.image)ft::free_image(m.image);for(auto&m:operator_models)if(m.image)ft::free_image(m.image);if(seal)ft::free_image(seal);ft::shutdown();return 0;
}
