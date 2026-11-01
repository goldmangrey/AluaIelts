/** Wall elapsed catches sleep on platforms where performance.now pauses.
 * Backward clock changes cannot extend the monotonic interval; forward changes
 * pause the editor conservatively and trigger a fresh server observation. */
export function elapsedSeconds(startPerformance:number,startWall:number,nowPerformance:number,nowWall:number) {
  return Math.max(0,nowPerformance-startPerformance,nowWall-startWall)/1000;
}
export function remainingSeconds(deadline:string,serverNow:string,elapsed:number) {
  return Math.max(0,Math.floor((Date.parse(deadline)-Date.parse(serverNow))/1000-elapsed));
}
