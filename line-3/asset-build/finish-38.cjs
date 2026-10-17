// Assemble imagegen pigment on the ancestor; preserves every pixel outside the mark.
// The generated wall temporarily occupies the final output path before assembly.
const fs = require('node:fs'), crypto = require('node:crypto');
const media = require('./png_codec.cjs');
const hash = b => crypto.createHash('sha256').update(b).digest('hex');
const source = 'artifacts/line-3/wall-v20.png';
const target = 'artifacts/line-3/wall-v21.png';
const original = fs.readFileSync(source), generated = fs.readFileSync(target);
if (hash(original) !== '1085ee6f9ab5a719f90260952e30b895dcf355530fbf645d06cc457a84dab3ab') throw Error('Wrong ancestor');
const old = media.decode(original), paint = media.decode(generated);
const out = {...old, pixels: Buffer.from(old.pixels)};
const crop = [950, 121, 82, 82], box = [900, 88, 82, 82];
let changed = 0, outside = 0;
for (let y = 0; y < box[3]; y++) for (let x = 0; x < box[2]; x++) {
  const sx = crop[0]+x, sy = crop[1]+y;
  // The pouch silhouette, not the surrounding generated rock or ancestral marks.
  if (sy < 125 || sy > 201) continue;
  const cx = 990, half = sy < 145 ? 23 : sy < 164 ? 15+(sy-145)*.65 : 37;
  if (Math.abs(sx-cx) > half) continue;
  const p = (sy*paint.width+sx)*3;
  const [r,g,b] = paint.pixels.subarray(p,p+3);
  const charcoal = r < 67 && g < 58 && b < 48;
  const ochre = r > 72 && r > g*1.65 && g > b*1.05;
  if (!charcoal && !ochre) continue;
  const color = ochre ? [146,57,27] : [39,29,21];
  const i = ((box[1]+y)*old.width+box[0]+x)*3;
  const alpha = ochre ? .73 : .77;
  for (let c=0;c<3;c++) out.pixels[i+c] = Math.round(old.pixels[i+c]*(1-alpha)+color[c]*alpha);
  if (!old.pixels.subarray(i,i+3).equals(out.pixels.subarray(i,i+3))) changed++;
}
for (let y=0;y<old.height;y++) for (let x=0;x<old.width;x++) {
  if (x>=box[0] && x<box[0]+box[2] && y>=box[1] && y<box[1]+box[3]) continue;
  const i=(y*old.width+x)*3;
  if (!old.pixels.subarray(i,i+3).equals(out.pixels.subarray(i,i+3))) outside++;
}
if (outside || changed < 500 || changed > 6000) throw Error('Preservation check failed');
const png = media.encode(out), jpg = media.thumbnail(out);
if (jpg.length > 100000 || !media.decode(png).pixels.equals(out.pixels)) throw Error('Format failure');
fs.writeFileSync(target,png);
fs.rmSync('artifacts/line-3/wall.png',{force:true});
fs.symlinkSync('wall-v21.png','artifacts/line-3/wall.png');
fs.writeFileSync('dist/line-3/38.jpg',jpg,{flag:'wx'});
const result = {source,source_sha256:hash(original),generated_sha256:hash(generated),output:target,
  output_sha256:hash(png),patch_xywh:box,generated_crop_xywh:crop,changed_pixels:changed,
  changed_pixels_outside_patch:outside,png_dimensions:[1254,1254],png_format:'RGB PNG',png_bytes:png.length,
  jpeg_dimensions:[512,512],jpeg_format:'JPEG',jpeg_bytes:jpg.length,
  method:'Built-in imagegen pouch pigment isolated by silhouette and earth-color thresholds, moved to bare rock and blended into unchanged ancestor.'};
fs.writeFileSync('line-3/asset-build/preservation-38.json',JSON.stringify(result,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify(result,null,2));
