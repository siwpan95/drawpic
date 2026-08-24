import tkinter as tk, time
import main

root = tk.Tk()
app = main.GlitchApp(root)
sel = app.generators[:3]
app.mode_var.set('video')
app.video_mode_var.set('showcase')
app.label_var.set(True)
app.w_var.set('480')
app.h_var.set('320')
app.dur_var.set('1')
app.fps_var.set('12')

t0 = time.time()
app._run_videos(sel, None)
dt = time.time() - t0

fracs, logs = [], []
while True:
    try:
        m = app.queue.get_nowait()
        if isinstance(m, tuple) and m[0] == 'FRAC':
            fracs.append(round(m[1] * 100))
        else:
            logs.append(m)
    except Exception:
        break

print('video showcase: 耗时 %.2fs, 进度条更新次数=%d, 末进度=%d%%' % (dt, len(fracs), fracs[-1] if fracs else -1))
print('进度采样 前/中/后:', fracs[:3], fracs[len(fracs)//2:len(fracs)//2+2], fracs[-2:])
print('日志条数=', len(logs))

# 图片模式分数
app.mode_var.set('image')
t0 = time.time()
app._run_images([app.generators[0]], None)
imgs = []
while True:
    try:
        m = app.queue.get_nowait()
        if isinstance(m, tuple) and m[0] == 'FRAC':
            imgs.append(round(m[1]*100))
    except Exception:
        break
print('image mode 进度:', imgs)
root.destroy()
print('OK')
