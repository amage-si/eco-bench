//! The GPUI side of the AMAGE Eco vs GPUI benchmark.
//!
//! `gpui-bench demo` reproduces the Eco integrated demo (Chromi
//! `examples/eco`): same font file, sizes, colors, layout rules, PNG and SVG,
//! and Kairo's button rules (Tab focuses, Space/Enter key-down presses,
//! key-up activates). `gpui-bench grid N` draws N labels and a counter.
//!
//! Like the Eco programs it logs one line per input batch and per redraw.
//! A line `auto <count> <interval_ms>` on stdin makes the program trigger
//! its own key-down/key-up pairs on a timer (used where synthetic input
//! cannot be targeted at the window, i.e. on Wayland).

use std::borrow::Cow;
use std::io::{BufRead, Write};
use std::sync::Arc;
use std::time::Duration;

use anyhow::Result;
use futures::StreamExt;
use gpui::{
    App, AssetSource, Bounds, Context, FocusHandle, Hsla, ImageSource, IntoElement, KeyDownEvent,
    KeyUpEvent, MouseMoveEvent, RenderImage, SharedString, TitlebarOptions, Window,
    WindowBackgroundAppearance, WindowBounds, WindowDecorations, WindowKind, WindowOptions, div,
    img, point, prelude::*, px, rgb, size, svg,
};
use image::ImageDecoder;

const FONT_PATH: &str = "/usr/share/fonts/liberation/LiberationSans-Regular.ttf";
const FONT_FAMILY: &str = "Liberation Sans";
const PNG_PATH: &str = "/usr/share/pixmaps/kitty.png";
const SVG_PATH: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/../../Splina/fixtures/heart-fill.svg");

/// Liberation Sans `hhea` (ascender - descender + lineGap) / unitsPerEm,
/// the line height Syllo uses: (1854 + 434 + 67) / 2048.
const LINE: f32 = 1.149_902_3;

// Colors of the Eco demo (Chromi examples/eco/ui.bend) and Mokko's theme.
const BACKGROUND: u32 = 0x0D141E;
const PANEL: u32 = 0x151A20;
const LINE_COLOR: u32 = 0x313A40;
const ACCENT: u32 = 0x40F3BE;
const HEART: u32 = 0xF35157;
const INK: u32 = 0xEEF1F9;
const MUTED: u32 = 0xB0C0CA;
const BUTTON: u32 = 0x245CCE;
const BUTTON_HOVER: u32 = 0x3170E6;
const BUTTON_PRESSED: u32 = 0x183F96;
const BUTTON_TEXT: u32 = 0xFFFFFF;
const FOCUS_RING: u32 = 0xA4C8FF;

const MEDIA_WIDTH: f32 = 256.0;
const GAP: f32 = 14.0;

// Grid scene: 31 columns of 28x12 cells from (16, 64), 10 px labels.
const GRID_COLUMNS: usize = 31;
const CELL_W: f32 = 28.0;
const CELL_H: f32 = 12.0;

fn color(c: u32) -> Hsla {
    rgb(c).into()
}

fn mono_ns() -> u64 {
    let mut ts = libc::timespec { tv_sec: 0, tv_nsec: 0 };
    // SAFETY: clock_gettime writes into the timespec we own.
    unsafe { libc::clock_gettime(libc::CLOCK_MONOTONIC, &mut ts) };
    ts.tv_sec as u64 * 1_000_000_000 + ts.tv_nsec as u64
}

fn log(line: std::fmt::Arguments) {
    let mut err = std::io::stderr().lock();
    let _ = err.write_fmt(line);
    let _ = err.write_all(b"\n");
}

/// Reads assets from the file system by path, as the Eco programs do.
struct Files;

impl AssetSource for Files {
    fn load(&self, path: &str) -> Result<Option<Cow<'static, [u8]>>> {
        Ok(Some(Cow::Owned(std::fs::read(path)?)))
    }

    fn list(&self, _path: &str) -> Result<Vec<SharedString>> {
        Ok(Vec::new())
    }
}

/// Decodes the PNG before the window opens, the way GPUI's own loader does
/// (RGBA to BGRA), so the first frame already contains it.
fn load_png(path: &str) -> Result<Arc<RenderImage>> {
    let bytes = std::fs::read(path)?;
    let mut decoder = image::codecs::png::PngDecoder::new(std::io::Cursor::new(bytes))?;
    let orientation = decoder.orientation()?;
    let mut picture = image::DynamicImage::from_decoder(decoder)?;
    picture.apply_orientation(orientation);
    let mut data = picture.into_rgba8();
    for pixel in data.chunks_exact_mut(4) {
        pixel.swap(0, 2);
    }
    Ok(Arc::new(RenderImage::new(smallvec::smallvec![image::Frame::new(data)])))
}

#[derive(Clone, Copy, PartialEq)]
enum Scene {
    Demo,
    Grid(usize),
}

struct Bench {
    scene: Scene,
    picture: Arc<RenderImage>,
    labels: Vec<SharedString>,
    root_focus: FocusHandle,
    button_focus: FocusHandle,
    pressed: bool,
    clicks: u32,
    redraws: u32,
    started: u64,
}

fn status(clicks: u32) -> String {
    match clicks {
        0 => "Clique no botão ou use Tab e Espaço.".to_string(),
        1 => "Ativado 1 vez.".to_string(),
        n => format!("Ativado {n} vezes."),
    }
}

fn text(content: impl Into<SharedString>, size: f32, ink: u32) -> gpui::Div {
    div()
        .text_size(px(size))
        .line_height(px(size * LINE))
        .text_color(color(ink))
        .child(content.into())
}

impl Bench {
    fn key_down(&mut self, event: &KeyDownEvent, window: &mut Window, cx: &mut Context<Self>) {
        let key = event.keystroke.key.as_str();
        log(format_args!("input: key-down {key}{}", if event.is_held { "r" } else { "" }));
        match key {
            "tab" => {
                window.focus(&self.button_focus, cx);
                cx.notify();
            }
            "space" | "enter" if !event.is_held && self.button_focus.is_focused(window) => {
                if !self.pressed {
                    self.pressed = true;
                    cx.notify();
                }
            }
            _ => {}
        }
    }

    fn key_up(&mut self, event: &KeyUpEvent, _window: &mut Window, cx: &mut Context<Self>) {
        let key = event.keystroke.key.as_str();
        log(format_args!("input: key-up {key}"));
        if matches!(key, "space" | "enter") && self.pressed {
            self.activate(cx);
        }
    }

    fn activate(&mut self, cx: &mut Context<Self>) {
        self.pressed = false;
        self.clicks += 1;
        log(format_args!("input: -> 1 activation(s)"));
        cx.notify();
    }

    /// Mokko's button: (label + 32) x 44, radius 10, the state's fill, and a
    /// 2 px focus ring inset 2 px with radius 9.
    fn button(&self, window: &Window, cx: &mut Context<Self>) -> impl IntoElement {
        let focused = self.button_focus.is_focused(window);
        let fill = if self.pressed { BUTTON_PRESSED } else { BUTTON };
        div()
            .id("button")
            .track_focus(&self.button_focus)
            .relative()
            .flex()
            .flex_none()
            .items_center()
            .justify_center()
            .h(px(44.0))
            .px(px(16.0))
            .rounded(px(10.0))
            .bg(color(fill))
            .when(!self.pressed, |b| b.hover(|s| s.bg(color(BUTTON_HOVER))))
            .active(|s| s.bg(color(BUTTON_PRESSED)))
            .on_click(cx.listener(|this, _, _, cx| this.activate(cx)))
            .when(focused, |b| {
                b.child(
                    div()
                        .absolute()
                        .top(px(2.0))
                        .left(px(2.0))
                        .right(px(2.0))
                        .bottom(px(2.0))
                        .rounded(px(9.0))
                        .border_2()
                        .border_color(color(FOCUS_RING)),
                )
            })
            .child(text("Ativar", 18.0, BUTTON_TEXT).whitespace_nowrap())
    }

    fn demo(&self, window: &Window, cx: &mut Context<Self>) -> gpui::Div {
        let viewport = window.viewport_size();
        let w = f32::from(viewport.width);
        let h = f32::from(viewport.height);
        // The panel is inset 24 px; the content 32 px inside it.
        let cw = (w - 112.0).max(1.0);
        let ch = (h - 112.0).max(0.0);
        let wide = w >= 760.0;
        let column = if wide { (cw - MEDIA_WIDTH - 40.0).max(120.0) } else { cw };

        let texts = div()
            .relative()
            .flex()
            .flex_col()
            .flex_none()
            .items_start()
            .gap(px(GAP))
            .w(px(column))
            .when(!wide, |c| c.h(px((ch - 420.0).max(0.0))))
            .child(
                div()
                    .absolute()
                    .top(px(-14.0))
                    .left_0()
                    .w(px(64.0))
                    .h(px(4.0))
                    .bg(color(ACCENT)),
            )
            .child(text("AMAGE Eco", 34.0, INK))
            .child(text("Uma janela, uma GPU, várias bibliotecas.", 19.0, MUTED))
            .child(text(
                "Texto real em Bend: ação, coração, café. A Ankra cuida da janela e dos eventos, \
                 a Voltra da GPU e o Chromi da lista de desenho.",
                16.0,
                INK,
            ))
            .child(self.button(window, cx))
            .child(text(status(self.clicks), 16.0, MUTED));

        let media = div()
            .flex()
            .flex_col()
            .flex_none()
            .items_center()
            .gap(px(GAP))
            .map(|m| {
                if wide {
                    m.w(px(MEDIA_WIDTH))
                } else {
                    m.w(px(cw)).h(px(ch.min(420.0)))
                }
            })
            .child(
                img(ImageSource::Render(self.picture.clone()))
                    .w(px(256.0))
                    .h(px(256.0))
                    .flex_none(),
            )
            .child(text("PNG decodificado pela Ocula", 13.0, MUTED).whitespace_nowrap())
            .child(
                svg()
                    .path(SVG_PATH)
                    .w(px(96.0))
                    .h(px(96.0))
                    .flex_none()
                    .text_color(color(HEART)),
            )
            .child(text("SVG interpretado pela Splina", 13.0, MUTED).whitespace_nowrap());

        div().child(
            div()
                .absolute()
                .left(px(24.0))
                .top(px(24.0))
                .w(px((w - 48.0).max(0.0)))
                .h(px((h - 48.0).max(0.0)))
                .rounded(px(18.0))
                .bg(color(PANEL))
                .border_1()
                .border_color(color(LINE_COLOR))
                // 31 px of padding inside the 1 px border: the content box is
                // the panel inset 32 px, as in Eco.
                .p(px(31.0))
                .flex()
                .map(|p| if wide { p.flex_row().justify_between() } else { p.flex_col() })
                .child(texts)
                .child(media),
        )
    }

    fn grid(&self, window: &Window, cx: &mut Context<Self>) -> gpui::Div {
        let count = format!("Ativações: {}", self.clicks);
        div()
            .child(
                div()
                    .absolute()
                    .left(px(16.0))
                    .top(px(8.0))
                    .flex()
                    .flex_row()
                    .items_center()
                    .gap(px(16.0))
                    .child(self.button(window, cx))
                    .child(text(count, 16.0, INK).whitespace_nowrap()),
            )
            .child(
                div()
                    .absolute()
                    .left(px(16.0))
                    .top(px(64.0))
                    .w(px(GRID_COLUMNS as f32 * CELL_W))
                    .flex()
                    .flex_row()
                    .flex_wrap()
                    .children(self.labels.iter().map(|label| {
                        div()
                            .w(px(CELL_W))
                            .h(px(CELL_H))
                            .flex_none()
                            .text_size(px(10.0))
                            .line_height(px(10.0 * LINE))
                            .text_color(color(MUTED))
                            .whitespace_nowrap()
                            .child(label.clone())
                    })),
            )
    }
}

impl Render for Bench {
    fn render(&mut self, window: &mut Window, cx: &mut Context<Self>) -> impl IntoElement {
        self.redraws += 1;
        log(format_args!(
            "redraw {} at {} ms",
            self.redraws,
            (mono_ns() - self.started) / 1_000_000
        ));
        let content = match self.scene {
            Scene::Demo => self.demo(window, cx),
            Scene::Grid(_) => self.grid(window, cx),
        };
        content
            .id("root")
            .track_focus(&self.root_focus)
            .on_key_down(cx.listener(Self::key_down))
            .on_key_up(cx.listener(Self::key_up))
            .on_mouse_move(cx.listener(|_, _: &MouseMoveEvent, _, _| log(format_args!("input: move"))))
            .relative()
            .size_full()
            .bg(color(BACKGROUND))
            .font_family(FONT_FAMILY)
    }
}

/// Pseudo-random waits for self-triggered batches (xorshift64, fixed seed):
/// a fixed interval that is a multiple of the frame period would land every
/// trigger at the same phase of the frame clock.
struct Jitter {
    state: u64,
    max_us: u64,
}

impl Jitter {
    fn next(&mut self) -> Duration {
        self.state ^= self.state << 13;
        self.state ^= self.state >> 7;
        self.state ^= self.state << 17;
        Duration::from_micros(self.state % (self.max_us + 1))
    }
}

/// A self-triggered batch: `count` key-down/key-up pairs, each `interval`
/// plus a pseudo-random wait apart, each timestamped right before the state
/// changes.
fn auto_batch(
    entity: gpui::WeakEntity<Bench>,
    count: u32,
    interval: Duration,
    mut jitter: Jitter,
    cx: &mut gpui::AsyncApp,
) -> gpui::Task<()> {
    cx.spawn(async move |cx| {
        for _ in 0..count {
            for down in [true, false] {
                cx.background_executor().timer(interval + jitter.next()).await;
                let ok = entity.update(cx, |this, cx| {
                    log(format_args!("auto {} {}", if down { "down" } else { "up" }, mono_ns()));
                    if down {
                        this.pressed = true;
                        cx.notify();
                    } else {
                        this.activate(cx);
                    }
                });
                if ok.is_err() {
                    return;
                }
            }
        }
        log(format_args!("auto done"));
    })
}

fn main() {
    let started = mono_ns();
    let args: Vec<String> = std::env::args().skip(1).collect();
    let scene = match args.first().map(String::as_str) {
        Some("grid") => Scene::Grid(args.get(1).and_then(|n| n.parse().ok()).unwrap_or(1000)),
        _ => Scene::Demo,
    };
    let title = match scene {
        Scene::Demo => "GPUI bench - demo".to_string(),
        Scene::Grid(n) => format!("GPUI bench - grid {n}"),
    };

    let font = std::fs::read(FONT_PATH).expect("reading the font");
    let picture = load_png(PNG_PATH).expect("decoding the PNG");
    let labels: Vec<SharedString> = match scene {
        Scene::Grid(n) => (1..=n).map(|i| SharedString::from(format!("{i:04}"))).collect(),
        Scene::Demo => Vec::new(),
    };

    // Control lines on stdin (a FIFO in benchmark runs), read off the main
    // thread so waiting for them never wakes the event loop.
    let (control_tx, mut control_rx) = futures::channel::mpsc::unbounded::<String>();
    std::thread::spawn(move || {
        for line in std::io::stdin().lock().lines() {
            let Ok(line) = line else { break };
            if control_tx.unbounded_send(line).is_err() {
                break;
            }
        }
    });

    gpui_platform::application().with_assets(Files).run(move |cx: &mut App| {
        cx.text_system()
            .add_fonts(vec![Cow::Owned(font)])
            .expect("loading the font");
        let bounds = Bounds {
            origin: point(px(0.0), px(0.0)),
            size: size(px(900.0), px(560.0)),
        };
        let window = cx
            .open_window(
                WindowOptions {
                    window_bounds: Some(WindowBounds::Windowed(bounds)),
                    titlebar: Some(TitlebarOptions {
                        title: Some(title.into()),
                        appears_transparent: false,
                        traffic_light_position: None,
                    }),
                    focus: false,
                    show: true,
                    kind: WindowKind::Normal,
                    is_movable: true,
                    app_id: Some("gpui-bench".to_string()),
                    window_background: WindowBackgroundAppearance::Opaque,
                    window_decorations: Some(WindowDecorations::Server),
                    window_min_size: Some(size(px(200.0), px(200.0))),
                    ..Default::default()
                },
                |window, cx| {
                    cx.new(|cx| {
                        let root_focus = cx.focus_handle();
                        window.focus(&root_focus, cx);
                        // Logged like Ankra's focus events, so input the
                        // benchmark did not send shows up in the log.
                        cx.observe_window_activation(window, |_, window, _| {
                            let active = window.is_window_active();
                            log(format_args!("input: {}", if active { "focus-in" } else { "focus-out" }));
                        })
                        .detach();
                        Bench {
                            scene,
                            picture,
                            labels,
                            root_focus,
                            button_focus: cx.focus_handle(),
                            pressed: false,
                            clicks: 0,
                            redraws: 0,
                            started,
                        }
                    })
                },
            )
            .expect("opening the window");
        let entity = window.update(cx, |_, _, cx| cx.entity().downgrade()).expect("the view");

        cx.on_window_closed(|cx, _| {
            if cx.windows().is_empty() {
                cx.quit();
            }
        })
        .detach();

        cx.spawn(async move |cx| {
            let mut batches = Vec::new();
            while let Some(line) = control_rx.next().await {
                let words: Vec<&str> = line.split_whitespace().collect();
                // auto <count> <interval ms> [<jitter ms> <seed>]
                if let ["auto", count, interval, rest @ ..] = words.as_slice() {
                    let count = count.parse().unwrap_or(30);
                    let interval = Duration::from_millis(interval.parse().unwrap_or(300));
                    let jitter_ms: f64 = rest.first().and_then(|j| j.parse().ok()).unwrap_or(0.0);
                    let seed: u64 = rest.get(1).and_then(|s| s.parse().ok()).unwrap_or(2026);
                    let jitter = Jitter { state: seed.max(1), max_us: (jitter_ms * 1000.0) as u64 };
                    log(format_args!("auto start {count} x {interval:?} + 0..{jitter_ms} ms"));
                    batches.push(auto_batch(entity.clone(), count, interval, jitter, cx));
                }
            }
        })
        .detach();
    });
}
