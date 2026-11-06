import {expect,type Locator,type Page} from "@playwright/test";
export async function watchSaveIndicators(page:Page){
 await page.evaluate(()=>{
  const seen:string[]=[];
  const scan=()=>document.querySelectorAll('[role="status"]').forEach(el=>{
   const text=el.textContent?.trim()||"";
   if(/^(Saved(?: on this device)?|Saving(?:…|\.\.\.| on this device…))$/i.test(text))seen.push(text);
  });
  Object.assign(window,{examSaveIndicators:seen});
  new MutationObserver(scan).observe(document.body,{subtree:true,childList:true,characterData:true});scan();
 });
}
export async function expectNoSaveIndicators(page:Page){
 expect(await page.evaluate(()=>(window as Window&{examSaveIndicators?:string[]}).examSaveIndicators)).toEqual([]);
}
export async function expectCenteredDialog(page:Page,dialog:Locator){
 await expect(dialog).toBeVisible();await expect(dialog).toHaveCSS("position","fixed");
 const rect=(await dialog.boundingBox())!,viewport=page.viewportSize()!;
 expect(Math.abs(rect.x+rect.width/2-viewport.width/2)).toBeLessThanOrEqual(2);
 expect(Math.abs(rect.y+rect.height/2-viewport.height/2)).toBeLessThanOrEqual(2);
 expect(rect.x).toBeGreaterThanOrEqual(15);expect(rect.y).toBeGreaterThanOrEqual(15);
 expect(rect.x+rect.width).toBeLessThanOrEqual(viewport.width-15);expect(rect.y+rect.height).toBeLessThanOrEqual(viewport.height-15);
 expect(await dialog.evaluate(el=>el.matches(":modal"))).toBe(true);
 expect(await dialog.evaluate(el=>getComputedStyle(el,"::backdrop").backgroundColor)).not.toBe("rgba(0, 0, 0, 0)");
 expect(await dialog.evaluate(el=>document.elementFromPoint(4,4)===el)).toBe(true);
}
