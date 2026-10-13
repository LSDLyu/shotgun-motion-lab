"""Run with: python3 -m unittest discover -s tests -p '*_test.py' -v.
Requires Playwright and Chromium; tests use a local server, no production access.
"""
import functools
import http.server
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

class BrowserChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory(prefix="shotgun-browser-")
        subprocess.run(["node", "--input-type=module", "-e", """
          import {mkdir,writeFile} from 'node:fs/promises';
          import {join} from 'node:path';
          import {renderGame} from './scripts/render-game.mjs';
          const root=process.argv[1];
          for(const locale of ['zh','en']){
            const path=join(root,locale==='en'?'en/games/shotgun':'games/shotgun');
            await mkdir(path,{recursive:true});
            const html=await renderGame({locale});
            await writeFile(join(path,'index.html'),html);
            if(locale==='zh')await writeFile(join(root,'index.html'),html);
          }
        """, cls.fixture.name], cwd=ROOT, check=True)
        cls.server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", 0), functools.partial(QuietHandler, directory=cls.fixture.name))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}/"
        cls.pw = sync_playwright().start()
        executable = os.environ.get("CHROMIUM_PATH") or shutil.which("chromium") or shutil.which("google-chrome")
        cls.browser = cls.pw.chromium.launch(executable_path=executable, headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.fixture.cleanup()

    def setUp(self):
        self.context = self.browser.new_context(viewport={"width": 1440, "height": 1000})
        self.context.set_default_timeout(8000)
        self.page = self.context.new_page()
        self.errors = []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [], "Unexpected browser errors")

    def open(self, init=None):
        if init:
            self.page.add_init_script(init)
        self.page.goto(self.url)

    def phase(self, value):
        expect(self.page.locator("#lab")).to_have_attribute("data-phase", str(value))

    def ready_with_buttons(self):
        self.page.locator('[data-action="pull"]').click()
        expect(self.page.locator('[data-action="push"]')).to_be_enabled()
        self.page.locator('[data-action="push"]').click()
        expect(self.page.locator('[data-action="fire"]')).to_be_enabled()

    def mock_sensors(self, motion="'granted'", orientation="'granted'"):
        self.open("""
        Object.defineProperty(window, 'DeviceMotionEvent', {configurable:true,value:class {
            static requestPermission(){ return Promise.resolve(%s); }
        }});
        Object.defineProperty(window, 'DeviceOrientationEvent', {configurable:true,value:class {
            static requestPermission(){ return Promise.resolve(%s); }
        }});
        window.sendMotion = (x=0,y=0,z=0,gravity=false) => {
          const event=new Event('devicemotion');
          Object.defineProperty(event,gravity?'accelerationIncludingGravity':'acceleration',{value:{x,y,z}});
          dispatchEvent(event);
        };
        window.sendOrientation=(beta=0,gamma=0)=>{
          const event=new Event('deviceorientation');
          Object.defineProperties(event,{beta:{value:beta},gamma:{value:gamma}});
          dispatchEvent(event);
        };
        """ % (motion, orientation))

    def samples(self, x=0, count=20, gravity=False):
        self.page.evaluate("""async ({x,count,gravity})=>{
          for(let i=0;i<count;i++){
            sendMotion(x,0,0,gravity);await new Promise(r=>setTimeout(r,50));
          }
        }""", {"x":x,"count":count,"gravity":gravity})

    def calibrate_sensor(self, gravity=False):
        self.page.locator("#sensor-toggle").click()
        expect(self.page.locator("#sensor-badge")).to_have_text("等待数据")
        self.page.evaluate("sendOrientation(0,0)")
        self.samples(gravity=gravity)
        expect(self.page.locator("#sensor-badge")).to_have_text("感应已连接")

    def test_interactive_sequence_and_transient_feedback(self):
        self.open()
        expect(self.page.locator('[data-action="push"]')).to_be_disabled()
        expect(self.page.locator('[data-action="fire"]')).to_be_disabled()
        self.ready_with_buttons()
        self.phase(2)
        self.page.locator('[data-action="fire"]').click()
        self.phase(3)
        expect(self.page.locator('[data-action="fire"]')).to_be_disabled()
        self.phase(4)
        expect(self.page.locator(".model.shot")).to_have_count(0)
        expect(self.page.locator("#motion-value")).to_have_text("—")
        expect(self.page.locator("#tilt-value")).to_have_text("—")

    def test_english_learning_controls_and_language_links(self):
        self.page.goto(self.url + "en/games/shotgun/")
        expect(self.page.locator("html")).to_have_attribute("lang", "en")
        expect(self.page.locator("#games-link")).to_have_attribute("href", "/en/games/")
        expect(self.page.locator("h1")).to_have_text("See the structure behind the motion.")
        self.ready_with_buttons()
        expect(self.page.locator("#phase-title")).to_have_text("Lock")
        self.page.locator('[data-action="fire"]').click()
        self.phase(4)
        self.page.locator('button[data-mode="cycle"]').click()
        self.page.locator("#play").click()
        expect(self.page.locator("#play")).to_have_text("Pause")
        self.page.locator("#play").click()
        self.page.locator('button[data-mode="learn"]').click()
        for name in ["stock", "receiver", "barrel", "magazine", "pump", "bolt", "carrier", "chamber"]:
            self.page.locator(f'[data-part-choice="{name}"]').click()
            self.assertFalse(self.page.locator("#part-description").evaluate("e=>/\\p{Script=Han}/u.test(e.textContent)"))
        self.page.locator("#detail-toggle").click()
        expect(self.page.locator("#detail-toggle")).to_have_text("Full view ↙")
        self.page.locator("#language-link").click()
        expect(self.page.locator("html")).to_have_attribute("lang", "zh-CN")
        expect(self.page.locator("#games-link")).to_have_attribute("href", "/games/")
        self.page.locator("#language-link").click()
        expect(self.page.locator("html")).to_have_attribute("lang", "en")

    def test_english_sensor_denial_and_no_data_messages(self):
        self.page.add_init_script("""
          Object.defineProperty(window,'DeviceMotionEvent',{configurable:true,value:class {
            static requestPermission(){return Promise.resolve('denied');}
          }});
          Object.defineProperty(window,'DeviceOrientationEvent',{configurable:true,value:undefined});
        """)
        self.page.goto(self.url + "en/games/shotgun/")
        self.page.locator("#sensor-toggle").click()
        expect(self.page.locator("#sensor-badge")).to_have_text("Permission denied")
        self.page.evaluate("DeviceMotionEvent.requestPermission=()=>Promise.resolve('granted')")
        self.page.clock.install()
        self.page.locator("#sensor-toggle").click()
        expect(self.page.locator("#sensor-badge")).to_have_text("Awaiting data")
        self.page.clock.fast_forward(8100)
        expect(self.page.locator("#sensor-badge")).to_have_text("No sensor data")
        expect(self.page.locator("#sensor-message")).to_contain_text("Cutaway views and cycle playback still work")
        self.page.locator('[data-action="pull"]').click()
        self.phase(0)

    def test_views_keep_phase_copy_gate_and_pose_in_sync(self):
        self.open()
        self.ready_with_buttons()
        for view in ["exterior","compare","cutaway"]:
            self.page.locator(f'button[data-view="{view}"]').click()
            self.phase(2)
            expect(self.page.locator("#phase-title")).to_have_text("闭锁")
            expect(self.page.locator('[data-action="fire"]')).to_be_enabled()
            expect(self.page.locator('.model[data-phase="2"]')).to_have_count(2)
        self.page.locator('button[data-mode="learn"]').click()
        self.page.locator('button[data-mode="interactive"]').click()
        self.phase(2)
        expect(self.page.locator('[data-action="fire"]')).to_be_enabled()

    def test_reset_cancels_pending_animation_and_retains_view(self):
        self.open()
        self.page.locator('button[data-view="compare"]').click()
        self.page.locator('[data-action="pull"]').click()
        self.page.locator("#reset").click()
        self.page.wait_for_timeout(800)
        self.phase(0)
        expect(self.page.locator("#lab")).to_have_attribute("data-gate","idle")
        expect(self.page.locator("#models")).to_have_attribute("data-view","compare")
        expect(self.page.locator('[data-action="push"]')).to_be_disabled()

    def test_cycle_play_pause_step_speed_and_single_cycle_end(self):
        self.open()
        self.page.clock.install()
        self.page.locator('button[data-mode="cycle"]').click()
        self.page.locator("#speed").select_option("0.5")
        self.page.locator("#play").click()
        self.page.clock.fast_forward(3500);self.phase(0)
        self.page.clock.fast_forward(200);self.phase(1)
        self.page.locator("#play").click()
        self.page.clock.fast_forward(8000);self.phase(1)
        self.page.locator("#next").click();self.phase(2)
        self.page.locator("#previous").click();self.phase(1)
        self.page.locator('[data-phase="5"]').click()
        self.page.locator("#play").click();self.phase(0)
        self.page.locator("#speed").select_option("1.5")
        for phase in range(1,6):
            self.page.clock.fast_forward(1250);self.phase(phase)
        self.page.clock.fast_forward(1250)
        expect(self.page.locator("#play")).to_have_text("播放循环")
        self.phase(5)
        self.page.locator("#repeat").check()
        self.page.locator("#play").click()
        for _ in range(6):
            self.page.clock.fast_forward(1250)
        self.phase(0)
        expect(self.page.locator("#play")).to_have_text("暂停")

    def test_part_selection_zoom_explosion_and_keyboard(self):
        self.open()
        self.page.locator('button[data-view="exterior"]').click()
        self.page.locator('button[data-mode="learn"]').click()
        expect(self.page.locator("[data-part-choice]")).to_have_count(8)
        self.page.locator('[data-part-choice="bolt"]').click()
        expect(self.page.locator("#models")).to_have_attribute("data-view","compare")
        expect(self.page.locator("#part-description")).to_contain_text("往复运动")
        self.page.locator("#detail-toggle").click()
        expect(self.page.locator("#cutaway-model svg")).to_have_attribute("viewBox","300 70 350 230")
        self.page.locator("#spread").fill("80")
        self.page.locator("#spread").dispatch_event("input")
        expect(self.page.locator("#spread-value")).to_have_text("80%")
        self.assertNotEqual(self.page.locator("#cutaway-model .carrier-layer").evaluate("e=>e.style.transform"),"translateY(0px)")
        self.page.locator('#cutaway-model [data-part="chamber"]').focus()
        self.page.keyboard.press("Enter")
        expect(self.page.locator("#part-description")).to_contain_text("膛室区域")
        self.page.locator('button[data-mode="interactive"]').click()
        self.assertEqual(self.page.locator("#cutaway-model .carrier-layer").evaluate("e=>e.style.transform"),"translateY(0px)")

    def test_mobile_desktop_controls_have_no_overflow_or_clipping(self):
        self.open()
        self.check_responsive_layout()

    def test_english_mobile_desktop_controls_have_no_overflow_or_clipping(self):
        self.page.goto(self.url + "en/games/shotgun/")
        self.check_responsive_layout()

    def check_responsive_layout(self):
        for width,height in [(320,740),(390,844),(620,800),(760,900),(844,390),(1024,768),(1440,1000)]:
            self.page.set_viewport_size({"width":width,"height":height})
            for mode in ["interactive","cycle","learn"]:
                self.page.locator(f'button[data-mode="{mode}"]').click()
                for view in ["cutaway","exterior","compare"]:
                    self.page.locator(f'button[data-view="{view}"]').click()
                    self.assertFalse(self.page.evaluate("document.documentElement.scrollWidth > innerWidth"), (width,mode,view))
                    clipped = self.page.evaluate("""()=>{
                      const bad=[];
                      for(const el of document.querySelectorAll('button')){
                        if(!el.checkVisibility()) continue;
                        const r=el.getBoundingClientRect();
                        for(let parent=el.parentElement;parent;parent=parent.parentElement){
                          const style=getComputedStyle(parent),p=parent.getBoundingClientRect();
                          if(['hidden','clip'].includes(style.overflowX)&&(r.left<p.left-1||r.right>p.right+1))bad.push(el.textContent);
                          if(['hidden','clip'].includes(style.overflowY)&&(r.top<p.top-1||r.bottom>p.bottom+1))bad.push(el.textContent);
                        }
                      }
                      return bad;
                    }""")
                    self.assertEqual(clipped,[],(width,mode,view,clipped))

    def test_unsupported_sensor_never_claims_calibrated(self):
        self.open("Object.defineProperty(window,'DeviceMotionEvent',{value:undefined,configurable:true});")
        self.page.locator("#sensor-toggle").click()
        expect(self.page.locator("#sensor-badge")).to_have_text("按钮模式")
        expect(self.page.locator("#sensor-message")).to_contain_text("不支持")
        expect(self.page.locator("#motion-value")).to_have_text("—")
        expect(self.page.locator("#calibrate")).to_be_disabled()

    def test_permission_denial_and_no_data_fallback(self):
        self.mock_sensors(motion="'denied'")
        self.page.locator("#sensor-toggle").click()
        expect(self.page.locator("#sensor-badge")).to_have_text("未获授权")
        self.page.evaluate("DeviceMotionEvent.requestPermission=()=>Promise.resolve('granted')")
        self.page.clock.install()
        self.page.locator("#sensor-toggle").click()
        expect(self.page.locator("#sensor-badge")).to_have_text("等待数据")
        self.page.clock.fast_forward(8100)
        expect(self.page.locator("#sensor-badge")).to_have_text("未收到数据")
        expect(self.page.locator("#motion-value")).to_have_text("—")

    def test_null_sensor_data_is_not_valid_zero(self):
        self.mock_sensors()
        self.page.clock.install()
        self.page.locator("#sensor-toggle").click()
        expect(self.page.locator("#sensor-badge")).to_have_text("等待数据")
        self.page.evaluate("""()=>{for(let i=0;i<50;i++)sendMotion(null,null,null)}""")
        self.page.clock.fast_forward(8100)
        expect(self.page.locator("#sensor-badge")).to_have_text("未收到数据")

    def test_calibration_motion_cycle_pause_and_resume(self):
        self.mock_sensors()
        self.calibrate_sensor()
        self.samples(count=8)  # re-arm at neutral
        self.samples(x=-4,count=5)
        expect(self.page.locator("#lab")).to_have_attribute("data-gate","opened")
        expect(self.page.locator('[data-action="push"]')).to_be_enabled()
        self.samples(count=24)
        self.samples(x=4,count=5)
        expect(self.page.locator('[data-action="fire"]')).to_be_enabled()
        self.samples(count=24)
        self.samples(x=-5,count=5)
        expect(self.page.locator("#lab")).to_have_attribute("data-gate","spent")
        self.phase(4)
        self.page.locator("#sensor-toggle").click()
        expect(self.page.locator("#sensor-badge")).to_have_text("已暂停")
        self.samples(x=10,count=2)
        expect(self.page.locator("#motion-value")).to_have_text("—")
        self.page.locator("#sensor-toggle").click()
        expect(self.page.locator("#sensor-badge")).to_have_text("等待数据")
        expect(self.page.locator("#calibrate")).to_be_disabled()

    def test_gravity_fallback_and_orientation_learning(self):
        self.mock_sensors()
        self.calibrate_sensor(gravity=True)
        self.page.locator('button[data-mode="learn"]').click()
        self.page.evaluate("sendOrientation(0,15)")
        expect(self.page.locator("#tilt-value")).to_have_text("+15°")
        expect(self.page.locator("#spread-value")).to_have_text("60%")
        self.page.locator("#calibrate").click()
        expect(self.page.locator("#sensor-badge")).to_have_text("正在校准")
        expect(self.page.locator("#motion-value")).to_have_text("—")
        expect(self.page.locator("#tilt-value")).to_have_text("—")

    def test_rotated_screen_maps_sensor_axis_and_recalibrates(self):
        self.mock_sensors()
        self.page.evaluate("Object.defineProperty(screen.orientation,'angle',{configurable:true,value:90})")
        self.calibrate_sensor()
        self.samples(count=8)
        self.page.evaluate("""async()=>{for(let i=0;i<6;i++){sendMotion(0,4,0);await new Promise(r=>setTimeout(r,50));}}""")
        expect(self.page.locator("#lab")).to_have_attribute("data-gate","opened")
        self.page.evaluate("screen.orientation.dispatchEvent(new Event('change'))")
        expect(self.page.locator("#sensor-badge")).to_have_text("正在校准")

    def test_motion_on_other_axes_prevents_false_calibration(self):
        self.mock_sensors()
        self.page.locator("#sensor-toggle").click()
        expect(self.page.locator("#sensor-badge")).to_have_text("等待数据")
        self.page.evaluate("""async()=>{
          for(let i=0;i<25;i++){sendMotion(0,i%2?8:-8,0);await new Promise(r=>setTimeout(r,50));}
        }""")
        expect(self.page.locator("#sensor-badge")).to_have_text("正在校准")
        expect(self.page.locator("#motion-value")).to_have_text("—")
        self.samples(count=27)
        expect(self.page.locator("#sensor-badge")).to_have_text("感应已连接")

    def test_orientation_permission_exception_keeps_motion_available(self):
        self.mock_sensors()
        self.page.evaluate("() => { DeviceOrientationEvent.requestPermission=()=>{throw new Error('orientation unavailable')}; }")
        self.calibrate_sensor()
        self.page.evaluate("sendOrientation(10,10)")
        expect(self.page.locator("#tilt-value")).to_have_text("—")
        expect(self.page.locator("#tilt-note")).to_contain_text("滑块")
        self.page.locator('button[data-mode="learn"]').click()
        self.page.locator("#spread").fill("50")
        self.page.locator("#spread").dispatch_event("input")
        expect(self.page.locator("#spread-value")).to_have_text("50%")

    def test_visibility_stops_sensor_playback_and_pending_actions(self):
        self.mock_sensors()
        self.calibrate_sensor()
        self.page.locator('button[data-mode="cycle"]').click()
        self.page.locator("#play").click()
        self.page.evaluate("""()=>{
          Object.defineProperty(document,'hidden',{value:true,configurable:true});
          document.dispatchEvent(new Event('visibilitychange'));
        }""")
        expect(self.page.locator("#sensor-badge")).to_have_text("已暂停")
        expect(self.page.locator("#play")).to_have_text("播放循环")
        self.page.wait_for_timeout(2000)
        self.phase(0)

    def test_reset_while_permission_is_pending_cancels_activation(self):
        self.mock_sensors()
        self.page.evaluate("() => { DeviceMotionEvent.requestPermission=()=>new Promise(resolve=>window.finishPermission=resolve); }")
        self.page.locator("#sensor-toggle").click()
        expect(self.page.locator("#sensor-badge")).to_have_text("等待授权")
        self.page.locator("#reset").click()
        self.page.evaluate("finishPermission('granted')")
        self.page.wait_for_timeout(100)
        expect(self.page.locator("#sensor-badge")).to_have_text("按钮模式")
        expect(self.page.locator("#sensor-toggle")).to_have_text("启用感应")

    def test_feedback_preferences_and_reduced_motion(self):
        self.context.grant_permissions([])
        self.page.emulate_media(reduced_motion="reduce")
        self.open()
        expect(self.page.locator("body")).to_have_attribute("data-reduced","true")
        self.page.locator("summary").click()
        expect(self.page.locator("#sound")).not_to_be_checked()
        self.page.locator("#sound").check()
        expect(self.page.locator("#sound-label")).to_have_text("已开启")
        self.page.locator("#volume").fill("40")
        self.page.locator("#volume").dispatch_event("input")
        expect(self.page.locator("#volume-value")).to_have_text("40%")
        self.page.locator("#sound").uncheck()
        expect(self.page.locator("#sound-label")).to_have_text("静音")
        self.page.locator("#reduced").uncheck()
        expect(self.page.locator("body")).to_have_attribute("data-reduced","false")

if __name__ == "__main__":
    unittest.main()
