#target illustrator
// Template; execute generated job scripts, not this file directly.
(function () {
    var cfg = __CONFIG__, stage = __STAGE__;
    var log = new File(cfg.job + '/' + stage + '.log');
    log.encoding = 'UTF-8'; log.open('w'); log.close();
    function record(s) { log.open('a'); log.writeln(s); log.close(); }
    function rgb(a) { var c = new RGBColor(); c.red=a[0]; c.green=a[1]; c.blue=a[2]; return c; }
    function sameFile(a,b) { return new File(a).fsName === new File(b).fsName; }
    function openClean(path) {
        for (var i=0;i<app.documents.length;i++) {
            var d=app.documents[i];
            var existing;
            try { existing=d.fullName; } catch(e) { continue; }
            if (!sameFile(existing,path)) continue;
            if (!d.saved) throw new Error('Unsaved changes in target document');
            d.close(SaveOptions.DONOTSAVECHANGES); break;
        }
        return app.open(new File(path));
    }
    function fresh(path) { if (new File(path).exists) throw new Error('File exists; choose a fresh output/job directory: '+path); }
    function saveAI(d,path) { var o=new IllustratorSaveOptions(); o.pdfCompatible=true; o.compressed=true; d.saveAs(new File(path),o); }
    function png(d,path) { var p=new ExportOptionsPNG24(); p.artBoardClipping=true; p.transparency=false; p.horizontalScale=100; p.verticalScale=100; var previous=app.userInteractionLevel; try { app.userInteractionLevel=UserInteractionLevel.DONTDISPLAYALERTS; d.exportFile(new File(path),ExportType.PNG24,p); } finally { app.userInteractionLevel=previous; } if(!new File(path).exists) throw new Error("PNG export missing: "+path); }
    function within(b,r) { return b[0]>=r[0] && b[2]<=r[2] && cfg.height-b[1]>=r[1] && cfg.height-b[3]<=r[3]; }
    function directItems(parent) {
        var result=[];
        for(var i=0;i<parent.pageItems.length;i++) if(parent.pageItems[i].parent===parent) result.push(parent.pageItems[i]);
        return result;
    }
    function fittedText(layer,item) {
        var tf=layer.textFrames.add(); tf.name=item.text;
        var a=tf.textRange.characterAttributes; a.textFont=app.textFonts.getByName(item.font); a.size=40; a.fillColor=rgb(item.color); tf.contents=item.text;
        tf.position=[0,0];
        var m=tf.duplicate().createOutline(), b=m.geometricBounds, r=item.bounds;
        tf.resize(100*(r[2]-r[0])/(b[2]-b[0]),100*(r[3]-r[1])/(b[1]-b[3])); m.remove();
        m=tf.duplicate().createOutline(); b=m.geometricBounds;
        tf.translate(r[0]-b[0],cfg.height-r[1]-b[1]); m.remove();
    }
    function verifyText(d) {
        if(!cfg.labels.length || d.textFrames.length!==cfg.labels.length) throw new Error('Editable text manifest/count missing or mismatched');
        var actual=[], expected=[];
        for(var n=0;n<d.textFrames.length;n++) actual.push(d.textFrames[n].contents);
        for(n=0;n<cfg.labels.length;n++) expected.push(cfg.labels[n].text);
        actual.sort(); expected.sort();
        for(n=0;n<expected.length;n++) if(actual[n]!==expected[n]) throw new Error('Text content mismatch');
        return actual;
    }
    var checkpoint=cfg.job+'/trace.ai', finalAI=cfg.output+'/figure.ai';
    try {
        record('Illustrator '+app.version+'; stage='+stage);
        if(stage==='inspect') {
            var env=new File(cfg.job+'/environment.txt'); env.encoding='UTF-8'; env.open('w');
            env.writeln('Illustrator '+app.version); env.writeln('Presets: '+app.tracingPresetsList.join(' | '));
            for(var i=0;i<app.textFonts.length;i++) env.writeln(app.textFonts[i].name);
            env.close();
        } else if(stage==='trace') {
            fresh(checkpoint);
            var preset=cfg.preset, presets=app.tracingPresetsList;
            if(!preset) for(i=0;i<presets.length;i++) if(presets[i]==='High Fidelity Photo' || presets[i]==='\u9ad8\u4fdd\u771f\u5ea6\u7167\u7247') preset=presets[i];
            if(!preset) throw new Error('Select the localized high fidelity preset from environment.txt and set manifest.preset');
            var d=app.open(new File(cfg.job+'/source.tif'));
            if(d.rasterItems.length!==1) throw new Error('Expected one source RasterItem');
            d.artboards[0].artboardRect=[0,cfg.height,cfg.width,0]; d.layers[0].name='01 Panels and connectors';
            var r=d.rasterItems[0]; r.width=cfg.width; r.height=cfg.height; r.position=[0,cfg.height];
            var t=r.trace(), opt=t.tracing.tracingOptions;
            if(!opt.loadFromPreset(preset)) throw new Error('Cannot load preset: '+preset);
            opt.pathFidelity=90; opt.cornerFidelity=80; opt.noiseFidelity=1;
            app.redraw(); record('Trace paths='+t.tracing.pathCount+'; colors='+t.tracing.usedColorCount);
            t.tracing.expandTracing().name='Original vector trace'; app.redraw();
            if(d.rasterItems.length || d.placedItems.length) throw new Error('Expanded trace still contains raster/placed art');
            saveAI(d,checkpoint); png(d,cfg.job+'/trace-preview.png');
            d.selection=null; app.executeMenuCommand('fitin');
        } else if(stage==='rebuild') {
            if(!cfg.labels.length) throw new Error('Restore the visible text with a nonempty manifest before producing final artwork');
            fresh(finalAI); fresh(cfg.output+'/figure.svg'); fresh(cfg.output+'/preview.png');
            for(i=0;i<cfg.labels.length;i++) app.textFonts.getByName(cfg.labels[i].font);
            d=openClean(checkpoint);
            var art=d.layers[0].groupItems[0], figures=d.layers.add(); figures.name='02 Illustrations';
            var repairs=d.layers.add(); repairs.name='03 Text background repairs';
            var texts=d.layers.add(); texts.name='04 Editable text';
            for(i=0;i<cfg.labels.length;i++) {
                var item=cfg.labels[i], b=item.bounds, pad=item.padding, box=[b[0]-pad,b[1]-pad,b[2]+pad,b[3]+pad];
                var all=directItems(art);
                for(var j=all.length-1;j>=0;j--) if(within(all[j].geometricBounds,box)) {
                    if(item.repair==='glyphs') {
                        var old=all[j], c=old.typename==='PathItem' && old.filled ? old.fillColor : null;
                        if(c && c.typename==='RGBColor' && Math.max(c.red,c.green,c.blue)<128) {
                            old.fillColor=rgb(item.background); old.stroked=false;
                            old.name='Background repair: '+item.text; old.move(repairs,ElementPlacement.PLACEATEND);
                        }
                    } else all[j].remove();
                }
                if(item.repair!=='glyphs') {
                    var patch=repairs.pathItems.rectangle(cfg.height-box[1],box[0],box[2]-box[0],box[3]-box[1]);
                    patch.stroked=false; patch.fillColor=rgb(item.background); patch.name='Background: '+item.text;
                }
                fittedText(texts,item);
                record("Editable text "+(i+1)+"/"+cfg.labels.length+": "+item.text);
            }
            for(i=0;i<cfg.groups.length;i++) {
                var region=cfg.groups[i], g=figures.groupItems.add(); g.name=region.name;
                all=directItems(art); var moved=0;
                for(j=0;j<all.length;j++) if(within(all[j].geometricBounds,region.bounds)) {all[j].move(g,ElementPlacement.PLACEATEND); moved++;}
                if(!moved) throw new Error('Empty illustration region: '+region.name);
                record(region.name+': '+moved+' objects');
            }
            repairs.locked=true; d.activeLayer=texts; d.selection=null; app.redraw();
            verifyText(d);
            saveAI(d,finalAI); png(d,cfg.output+'/preview.png');
            var svg=new ExportOptionsSVG(); svg.fontType=SVGFontType.SVGFONT; svg.fontSubsetting=SVGFontSubsetting.GLYPHSUSED; svg.coordinatePrecision=3;
            d.exportFile(new File(cfg.output+'/figure.svg'),ExportType.SVG,svg);
            // Re-assert the native AI save target after SVG export; never call blind save().
            saveAI(d,finalAI); app.executeMenuCommand('fitin');
        } else if(stage==='verify') {
            d=openClean(finalAI);
            var actual=verifyText(d);
            if(d.rasterItems.length || d.placedItems.length || d.pathItems.length===0) throw new Error('Expected vector artwork without raster/placed images');
            var ab=d.artboards[0].artboardRect;
            if(Math.abs(ab[2]-ab[0]-cfg.width)>0.01 || Math.abs(ab[1]-ab[3]-cfg.height)>0.01) throw new Error('Artboard dimensions mismatch');
            record('AI='+d.fullName.fsName); record('Text frames='+actual.length+'; paths='+d.pathItems.length+'; raster=0; placed=0');
            var groupCount=d.layers.getByName('02 Illustrations').groupItems.length;
            if(groupCount!==cfg.groups.length) throw new Error('Illustration group count mismatch');
            record('Illustration groups='+groupCount);
            for(i=0;i<actual.length;i++) record('Text: '+actual[i]);
            d.selection=null; app.executeMenuCommand('fitin');
        } else if(stage==='live') {
            fresh(cfg.output+'/figure-live.ai');
            var source=openClean(finalAI);
            verifyText(source);
            function channels(c) {
                if(c.typename!=='RGBColor') throw new Error('Live mode expects RGB artwork from this workflow');
                return [c.red,c.green,c.blue];
            }
            function capture(node) {
                var out={kind:node.typename,name:node.name,opacity:node.opacity};
                if(node.typename==='GroupItem') {
                    if(node.clipped) throw new Error('Clipping groups need a separate playback adapter');
                    out.children=[]; var children=directItems(node);
                    for(var q=0;q<children.length;q++) out.children.push(capture(children[q]));
                } else if(node.typename==='PathItem') {
                    out.closed=node.closed; out.filled=node.filled; out.stroked=node.stroked; out.evenodd=node.evenodd;
                    if(out.filled) out.fill=channels(node.fillColor);
                    if(out.stroked) {out.stroke=channels(node.strokeColor);out.strokeWidth=node.strokeWidth;}
                    out.points=[];
                    for(q=0;q<node.pathPoints.length;q++) {
                        var p=node.pathPoints[q]; out.points.push([p.anchor,p.leftDirection,p.rightDirection,p.pointType]);
                    }
                } else if(node.typename==='TextFrame') {
                    var a=node.textRange.characterAttributes;
                    out.text=node.contents; out.position=node.position; out.font=a.textFont.name;
                    out.size=a.size; out.horizontal=a.horizontalScale; out.vertical=a.verticalScale; out.fill=channels(a.fillColor);
                } else {throw new Error('Unsupported live object: '+node.typename);}
                return out;
            }
            // Read native geometry once before drawing; avoid cross-document duplicate() MRAP errors.
            var layers=[];
            for(i=0;i<source.layers.length;i++) {
                var sl=source.layers[i], layer={name:sl.name,locked:sl.locked,visible:sl.visible,children:[]};
                var sourceItems=directItems(sl);
                for(j=0;j<sourceItems.length;j++) layer.children.push(capture(sourceItems[j]));
                layers.push(layer);
            }
            var live=app.documents.add(DocumentColorSpace.RGB,cfg.width,cfg.height);
            live.artboards[0].artboardRect=[0,cfg.height,cfg.width,0];
            var empty=live.layers[0], count=0;
            app.executeMenuCommand('fitin'); app.redraw();
            function playback(children,target) {
                for(var k=children.length-1;k>=0;k--) {
                    var child=children[k], made;
                    if(child.kind==='GroupItem') { made=target.groupItems.add(); playback(child.children,made); }
                    else if(child.kind==='PathItem') {
                        made=target.pathItems.add(); var anchors=[];
                        for(var q=0;q<child.points.length;q++) anchors.push(child.points[q][0]);
                        made.setEntirePath(anchors);
                        for(q=0;q<child.points.length;q++) {
                            var point=made.pathPoints[q];point.leftDirection=child.points[q][1];point.rightDirection=child.points[q][2];point.pointType=child.points[q][3];
                        }
                        made.closed=child.closed;made.filled=child.filled;made.stroked=child.stroked;made.evenodd=child.evenodd;
                        if(child.filled) made.fillColor=rgb(child.fill);
                        if(child.stroked) {made.strokeColor=rgb(child.stroke);made.strokeWidth=child.strokeWidth;}
                        count++;
                    } else {
                        made=target.textFrames.add();made.contents=child.text;
                        var attr=made.textRange.characterAttributes;
                        attr.textFont=app.textFonts.getByName(child.font);attr.size=child.size;attr.horizontalScale=child.horizontal;attr.verticalScale=child.vertical;attr.fillColor=rgb(child.fill);
                        made.position=child.position;count++;
                    }
                    made.name=child.name;made.opacity=child.opacity;
                    if(count%8===0) {live.activate(); app.redraw(); $.sleep(40);}
                }
            }
            for(i=layers.length-1;i>=0;i--) {
                var sl=layers[i], dl=live.layers.add(); dl.name=sl.name;
                playback(sl.children,dl); dl.visible=sl.visible; dl.locked=sl.locked;
                live.activate(); app.redraw(); $.sleep(120);
            }
            empty.remove(); live.selection=null; app.redraw();
            verifyText(live);
            if(live.pathItems.length!==source.pathItems.length || live.textFrames.length!==source.textFrames.length) throw new Error('Live playback object count mismatch');
            saveAI(live,cfg.output+'/figure-live.ai'); png(live,cfg.output+'/preview-live.png'); saveAI(live,cfg.output+'/figure-live.ai');
            record('Created native objects progressively: '+count);
        }
        record('DONE');
    } catch(e) {record('ERROR: '+e+'; line='+e.line);}
    log.close();
}());
