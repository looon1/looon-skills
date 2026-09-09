#target illustrator
#targetengine "looon_live_drawing"
// Template; execute generated job scripts, not this file directly.
(function () {
    var cfg = __CONFIG__, stage = __STAGE__;
    if(stage==='live' && $.global.looonLivePanel && !$.global.looonLivePanel.closed && $.global.looonLivePanel.job===cfg.job) {
        $.global.looonLivePanel.window.show();$.global.looonLivePanel.window.active=true;
        var resumed=new File(cfg.job+'/live.log');resumed.encoding='UTF-8';resumed.open('a');
        resumed.writeln('READY - existing controller shown');
        resumed.close();return;
    }
    var log = new File(cfg.job + '/' + stage + '.log');
    log.encoding = 'UTF-8'; log.open('w'); log.close();
    function record(s) { log.open('a'); log.writeln(s); log.close(); }
    function rgb(a) { var c = new RGBColor(); c.red=a[0]; c.green=a[1]; c.blue=a[2]; return c; }
    function sameFile(a,b) { return new File(a).fsName === new File(b).fsName; }
    function openClean(path) {
        var matches=[];
        for (var i=0;i<app.documents.length;i++) {
            var d=app.documents[i];
            var existing;
            try { existing=String(d.fullName); } catch(e) { continue; }
            if (!sameFile(existing,path)) continue;
            if (!d.saved) throw new Error('Unsaved changes in target document');
            matches.push(d);
        }
        for(i=matches.length-1;i>=0;i--) matches[i].close(SaveOptions.DONOTSAVECHANGES);
        return app.open(new File(path));
    }
    function fresh(path) { if (new File(path).exists) throw new Error('File exists; choose a fresh output/job directory: '+path); }
    function saveAI(d,path) { var o=new IllustratorSaveOptions(); o.pdfCompatible=true; o.compressed=true; var previous=app.userInteractionLevel; try { app.userInteractionLevel=UserInteractionLevel.DONTDISPLAYALERTS; d.saveAs(new File(path),o); } finally { app.userInteractionLevel=previous; } }
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
    function nativePaint(d,value) {
        if(value instanceof Array) return rgb(value);
        var g=d.gradients.add();g.type=GradientType.LINEAR;
        for(var s=0;s<value.stops.length;s++) {
            var stop=s<g.gradientStops.length?g.gradientStops[s]:g.gradientStops.add();
            stop.rampPoint=value.stops[s][0];stop.color=rgb(value.stops[s][1]);stop.opacity=100;
        }
        var color=new GradientColor();color.gradient=g;color.origin=value.origin;color.length=value.length;
        return color;
    }
    function nativeElement(d,layer,item) {
        var parent=layer,head=null;
        if(item.arrow) {parent=layer.groupItems.add();parent.name=item.name;}
        var p;
        if(item.type==='rect') p=parent.pathItems.rectangle(cfg.height-item.bounds[1],item.bounds[0],item.bounds[2]-item.bounds[0],item.bounds[3]-item.bounds[1]);
        else if(item.type==='ellipse') p=parent.pathItems.ellipse(cfg.height-item.bounds[1],item.bounds[0],item.bounds[2]-item.bounds[0],item.bounds[3]-item.bounds[1]);
        else {
            p=parent.pathItems.add();var anchors=[];
            for(var n=0;n<item.points.length;n++) anchors.push([item.points[n][0][0],cfg.height-item.points[n][0][1]]);
            p.setEntirePath(anchors);
            for(n=0;n<item.points.length;n++) {
                var point=item.points[n];
                if(point.length>1) {p.pathPoints[n].leftDirection=[point[1][0],cfg.height-point[1][1]];p.pathPoints[n].rightDirection=[point[2][0],cfg.height-point[2][1]];}
            }
            p.closed=!!item.closed;
        }
        p.name=item.name;p.filled=!!item.fill;if(item.fill)p.fillColor=nativePaint(d,item.fill);
        if(item.fill&&!(item.fill instanceof Array))p.rotate(item.fill.angle||0,false,false,true,false,Transformation.CENTER);
        p.stroked=!!item.stroke;
        if(item.stroke) {p.strokeColor=rgb(item.stroke);p.strokeWidth=item.width||2;p.strokeCap=StrokeCap.ROUNDENDCAP;p.strokeJoin=StrokeJoin.ROUNDENDJOIN;if(item.dashes)p.strokeDashes=item.dashes;}
        p.opacity=item.opacity===undefined?100:item.opacity;
        if(item.arrow) {
            var points=p.pathPoints,last=points[points.length-1],end=last.anchor,from=last.leftDirection;
            if(end[0]===from[0]&&end[1]===from[1])from=points[points.length-2].anchor;
            var dx=end[0]-from[0],dy=end[1]-from[1],length=Math.sqrt(dx*dx+dy*dy),ux=dx/length,uy=dy/length;
            var back=[end[0]-ux*item.arrow[0],end[1]-uy*item.arrow[0]],half=item.arrow[1]/2;
            head=parent.pathItems.add();head.setEntirePath([end,[back[0]-uy*half,back[1]+ux*half],[back[0]+uy*half,back[1]-ux*half]]);head.closed=true;head.stroked=false;head.fillColor=rgb(item.stroke);head.name=item.name+' head';
            var trim=item.arrow[0]*0.65;p.pathPoints[points.length-1].anchor=[end[0]-ux*trim,end[1]-uy*trim];
        }
        return parent===layer?p:parent;
    }
    function applyNativeLayout(d) {
        var layout=cfg.nativeLayout,base=d.layers.getByName('01 Panels and connectors'),art=base.groupItems[0],figures=d.layers.getByName('02 Illustrations');
        for(var r=0;r<layout.regions.length;r++) {
            var region=layout.regions[r],group=figures.groupItems.add();group.name=region.name;var items=directItems(art);
            for(var n=0;n<items.length;n++)if(within(items[n].geometricBounds,region.bounds))items[n].move(group,ElementPlacement.PLACEATEND);
            if(!group.pageItems.length)throw new Error('Empty retained illustration: '+region.name);
        }
        art.remove();base.name='01 Native background';
        var repairs=d.layers.getByName('03 Text background repairs');repairs.locked=false;
        for(n=repairs.pageItems.length-1;n>=0;n--) {
            var keep=false,b=repairs.pageItems[n].geometricBounds,regions=cfg.groups.concat(layout.regions);
            for(r=0;r<regions.length;r++)if(within(b,regions[r].bounds))keep=true;
            if(!keep)repairs.pageItems[n].remove();
        }
        for(r=0;r<(layout.removeTraced||[]).length;r++) {
            var rule=layout.removeTraced[r],g=figures.groupItems.getByName(rule.group);
            for(n=g.pathItems.length-1;n>=0;n--) {
                var old=g.pathItems[n],c=old.filled?old.fillColor:null;
                if(c&&c.typename==='RGBColor'&&Math.max(c.red,c.green,c.blue)<rule.maxGray&&Math.max(c.red,c.green,c.blue)-Math.min(c.red,c.green,c.blue)<35&&within(old.geometricBounds,rule.bounds))old.remove();
            }
        }
        var foreground=d.layers.add();foreground.name='05 Native geometry';
        for(r=0;r<layout.elements.length;r++)nativeElement(d,layout.elements[r].background?base:foreground,layout.elements[r]);
        repairs.locked=true;record('Native geometry='+layout.elements.length+'; complex illustration groups='+figures.groupItems.length);
    }
    function verifyNative(d) {
        if(!cfg.nativeLayout)return;
        for(var n=0;n<cfg.nativeLayout.elements.length;n++) {
            var item=cfg.nativeLayout.elements[n],layer=d.layers.getByName(item.background?'01 Native background':'05 Native geometry'),p;
            if(item.arrow) {var g=layer.groupItems.getByName(item.name);if(g.pathItems.length!==2)throw new Error('Arrow must have a native shaft and head');p=g.pathItems.getByName(item.name);}
            else p=layer.pathItems.getByName(item.name);
            var count=item.type==='path'?item.points.length:4;
            if(p.pathPoints.length!==count||p.stroked!==!!item.stroke)throw new Error('Native geometry mismatch: '+item.name);
            if(item.stroke&&Math.abs(p.strokeWidth-(item.width||2))>0.01)throw new Error('Native stroke width mismatch');
            if(item.dashes) {var dash=p.strokeDashes;if(dash.length!==item.dashes.length)throw new Error('Native dash pattern missing');for(var q=0;q<dash.length;q++)if(Math.abs(dash[q]-item.dashes[q])>0.01)throw new Error('Native dash pattern mismatch');}
        }
        record('Verified native elements='+cfg.nativeLayout.elements.length);
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
            if(cfg.nativeLayout)applyNativeLayout(d);
            repairs.locked=true; d.activeLayer=texts; d.selection=null; app.redraw();
            verifyText(d);
            verifyNative(d);
            saveAI(d,finalAI); png(d,cfg.output+'/preview.png');
            var svg=new ExportOptionsSVG(); svg.fontType=SVGFontType.SVGFONT; svg.fontSubsetting=SVGFontSubsetting.GLYPHSUSED; svg.coordinatePrecision=3;
            d.exportFile(new File(cfg.output+'/figure.svg'),ExportType.SVG,svg);
            // Re-assert the native AI save target after SVG export; never call blind save().
            saveAI(d,finalAI); app.executeMenuCommand('fitin');
        } else if(stage==='structure') {
            if(!cfg.nativeLayout||!cfg.nativeLayout.elements.length)throw new Error('Native layout manifest missing');
            fresh(finalAI);d=openClean(cfg.job+'/source.ai');verifyText(d);applyNativeLayout(d);verifyText(d);verifyNative(d);
            d.selection=null;app.redraw();saveAI(d,finalAI);png(d,cfg.output+'/preview.png');saveAI(d,finalAI);app.executeMenuCommand('fitin');
        } else if(stage==='verify') {
            d=openClean(finalAI);
            var actual=verifyText(d);
            verifyNative(d);
            if(d.rasterItems.length || d.placedItems.length || d.pathItems.length===0) throw new Error('Expected vector artwork without raster/placed images');
            var ab=d.artboards[0].artboardRect;
            if(Math.abs(ab[2]-ab[0]-cfg.width)>0.01 || Math.abs(ab[1]-ab[3]-cfg.height)>0.01) throw new Error('Artboard dimensions mismatch');
            record('AI='+d.fullName.fsName); record('Text frames='+actual.length+'; paths='+d.pathItems.length+'; raster=0; placed=0');
            var groupCount=d.layers.getByName('02 Illustrations').groupItems.length;
            if(groupCount!==cfg.groups.length+(cfg.nativeLayout?cfg.nativeLayout.regions.length:0)) throw new Error('Illustration group count mismatch');
            record('Illustration groups='+groupCount);
            for(i=0;i<actual.length;i++) record('Text: '+actual[i]);
            d.selection=null; app.executeMenuCommand('fitin');
        } else if(stage==='live') {
            if(!cfg.nativeLayout)throw new Error('Prepare native frames, connectors and backgrounds before live playback');
            fresh(cfg.output+'/figure-live.ai');fresh(cfg.output+'/preview-live.png');
            var source=openClean(finalAI);
            verifyText(source);
            function channels(c) {
                if(c.typename!=='RGBColor') throw new Error('Live mode expects RGB artwork from this workflow');
                return [c.red,c.green,c.blue];
            }
            function fillState(node) {
                var c=node.fillColor;
                if(c.typename==='RGBColor')return channels(c);
                if(c.typename!=='GradientColor'||c.gradient.type!==GradientType.LINEAR)throw new Error('Unsupported live fill');
                for(var s=0;s<cfg.nativeLayout.elements.length;s++)if(cfg.nativeLayout.elements[s].name===node.name&&cfg.nativeLayout.elements[s].fill.stops)return cfg.nativeLayout.elements[s].fill;
                throw new Error('Gradient needs its native layout definition: '+node.name);
            }
            function capture(node) {
                var out={kind:node.typename,name:node.name,opacity:node.opacity};
                if(node.typename==='GroupItem') {
                    if(node.clipped) throw new Error('Clipping groups need a separate playback adapter');
                    out.children=[]; var children=directItems(node);
                    for(var q=0;q<children.length;q++) out.children.push(capture(children[q]));
                } else if(node.typename==='PathItem') {
                    out.closed=node.closed; out.filled=node.filled; out.stroked=node.stroked; out.evenodd=node.evenodd;
                    if(out.filled) out.fill=fillState(node);
                    if(out.stroked) {out.stroke=channels(node.strokeColor);out.strokeWidth=node.strokeWidth;out.dashes=node.strokeDashes;out.dashOffset=node.strokeDashOffset;out.roundCap=node.strokeCap===StrokeCap.ROUNDENDCAP;out.squareCap=node.strokeCap===StrokeCap.PROJECTINGENDCAP;out.roundJoin=node.strokeJoin===StrokeJoin.ROUNDENDJOIN;out.bevelJoin=node.strokeJoin===StrokeJoin.BEVELENDJOIN;out.miter=node.strokeMiterLimit;}
                    out.points=[];
                    for(q=0;q<node.pathPoints.length;q++) {
                        var p=node.pathPoints[q]; out.points.push([p.anchor,p.leftDirection,p.rightDirection,p.pointType===PointType.SMOOTH]);
                    }
                } else if(node.typename==='TextFrame') {
                    var a=node.characters[0].characterAttributes;
                    out.text=node.contents; out.position=node.position; out.font=a.textFont.name;
                    out.size=a.size; out.horizontal=a.horizontalScale; out.vertical=a.verticalScale; out.fill=channels(a.fillColor);
                    out.characters=[];
                    for(q=0;q<node.characters.length;q++) {
                        a=node.characters[q].characterAttributes;
                        out.characters.push([a.textFont.name,a.size,a.horizontalScale,a.verticalScale,a.baselineShift,a.tracking,channels(a.fillColor)]);
                    }
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
            var token='LooonLive-'+new Date().getTime(), operations=[], names=[], serial=0;
            function flatten(children,parent) {
                for(var k=children.length-1;k>=0;k--) {
                    var child=children[k]; child.parent=parent;
                    if(child.kind==='GroupItem') {
                        child.id=token+'-'+(++serial);
                        operations.push({kind:'GroupItem',id:child.id,parent:parent,opacity:child.opacity});
                        names.push({kind:'GroupItem',id:child.id,name:child.name});
                        flatten(child.children,child.id);
                    } else operations.push(child);
                }
            }
            for(i=layers.length-1;i>=0;i--) {
                var layer=layers[i], id=token+'-'+(++serial);layer.id=id;
                operations.push({kind:'Layer',id:id});
                names.push({kind:'Layer',id:id,name:layer.name,locked:layer.locked,visible:layer.visible});
            }
            for(i=layers.length-1;i>=0;i--)if(layers[i].name!=='02 Illustrations')flatten(layers[i].children,layers[i].id);
            var staticCount=operations.length;
            for(i=layers.length-1;i>=0;i--)if(layers[i].name==='02 Illustrations')flatten(layers[i].children,layers[i].id);
            var expectedPaths=source.pathItems.length, expectedTexts=source.textFrames.length;
            var steps=new Folder(cfg.job+'/live-steps-'+token); steps.create();
            // Each file is a separate Illustrator scripting transaction. Never draw a whole job in one callback.
            function drawBatch(token,ops,finish,names,expectedPaths,expectedTexts,progress,batchIndex,totalBatches) {
                token=String(token);var d=null;
                for(var v=0;v<app.documents.length;v++) {
                    try {app.documents[v].layers.getByName(token);d=app.documents[v];break;} catch(ignore) {}
                }
                if(!d) throw new Error('Live document was closed or its marker layer was changed');
                d.activate();var madeHere={};
                function target(id) {
                    if(madeHere[id]) return madeHere[id];
                    for(var t=0;t<d.layers.length;t++) if(d.layers[t].name===id) return d.layers[t];
                    for(t=0;t<d.groupItems.length;t++) if(d.groupItems[t].name===id) return d.groupItems[t];
                    throw new Error('Live parent missing: '+id);
                }
                for(var k=0;k<ops.length;k++) {
                    var child=ops[k], made;
                    if(child.kind==='Layer') {made=d.layers.add();made.name=child.id;madeHere[child.id]=made;continue;}
                    var parent=target(child.parent);
                    if(child.kind==='GroupItem') {made=parent.groupItems.add();made.name=child.id;made.opacity=child.opacity;madeHere[child.id]=made;continue;}
                    if(child.kind==='PathItem') {
                        made=parent.pathItems.add(); var anchors=[];
                        for(var q=0;q<child.points.length;q++) anchors.push(child.points[q][0]);
                        made.setEntirePath(anchors);
                        for(q=0;q<child.points.length;q++) {
                            var p=made.pathPoints[q];p.leftDirection=child.points[q][1];p.rightDirection=child.points[q][2];
                            p.pointType=child.points[q][3]?PointType.SMOOTH:PointType.CORNER;
                        }
                        made.closed=child.closed;made.filled=child.filled;made.stroked=child.stroked;made.evenodd=child.evenodd;
                        if(child.filled) made.fillColor=nativePaint(d,child.fill);
                        if(child.filled&&!(child.fill instanceof Array))made.rotate(child.fill.angle||0,false,false,true,false,Transformation.CENTER);
                        if(child.stroked) {made.strokeColor=rgb(child.stroke);made.strokeWidth=child.strokeWidth;made.strokeDashes=child.dashes;made.strokeDashOffset=child.dashOffset;made.strokeCap=child.roundCap?StrokeCap.ROUNDENDCAP:(child.squareCap?StrokeCap.PROJECTINGENDCAP:StrokeCap.BUTTENDCAP);made.strokeJoin=child.roundJoin?StrokeJoin.ROUNDENDJOIN:(child.bevelJoin?StrokeJoin.BEVELENDJOIN:StrokeJoin.MITERENDJOIN);made.strokeMiterLimit=child.miter;}
                    } else {
                        made=parent.textFrames.add();var a=made.textRange.characterAttributes;
                        a.textFont=app.textFonts.getByName(child.font);a.size=child.size;a.horizontalScale=child.horizontal;a.verticalScale=child.vertical;a.fillColor=rgb(child.fill);
                        made.contents=child.text;
                        for(q=0;q<child.characters.length;q++) {
                            var style=child.characters[q];a=made.characters[q].characterAttributes;
                            a.textFont=app.textFonts.getByName(style[0]);a.size=style[1];a.horizontalScale=style[2];a.verticalScale=style[3];a.baselineShift=style[4];a.tracking=style[5];a.fillColor=rgb(style[6]);
                        }
                        made.position=child.position;
                    }
                    made.name=child.name;made.opacity=child.opacity;
                }
                d.selection=null;app.redraw();
                record('PROGRESS '+progress+'; paths='+d.pathItems.length+'; text='+d.textFrames.length+'; time='+new Date().getTime());
                if(finish) {
                    for(k=0;k<names.length;k++) {
                        var info=names[k], item=target(info.id);item.name=info.name;
                        if(info.kind==='Layer') {item.visible=info.visible;item.locked=info.locked;}
                    }
                    d.layers.getByName(token).remove();
                    verifyText(d);
                    verifyNative(d);
                    if(d.pathItems.length!==expectedPaths || d.textFrames.length!==expectedTexts || d.rasterItems.length || d.placedItems.length) throw new Error('Live object count mismatch');
                    saveAI(d,cfg.output+'/figure-live.ai');png(d,cfg.output+'/preview-live.png');saveAI(d,cfg.output+'/figure-live.ai');
                    record('Verified text='+d.textFrames.length+'; paths='+d.pathItems.length+'; raster=0; placed=0');record('DONE');
                }
                var cursor=new File(cfg.job+'/live-cursor.txt');cursor.open('w');cursor.write(batchIndex+1);cursor.close();
                var view=$.global.looonLivePanel && $.global.looonLivePanel.job===cfg.job ? $.global.looonLivePanel.window : null;
                if(view) {view.children[0].text=(finish?'Done':'Completed')+' - batch '+(batchIndex+1)+' / '+totalBatches;view.children[1].value=batchIndex+1;if(finish)for(var b=0;b<view.children[2].children.length;b++)view.children[2].children[b].enabled=false;view.update();}
                return progress;
            }
            var worker='var cfg='+cfg.toSource()+';\nvar log=new File(cfg.job+"/live.log");log.encoding="UTF-8";\n'+
                'var record='+record.toSource()+';var rgb='+rgb.toSource()+';var nativePaint='+nativePaint.toSource()+';var saveAI='+saveAI.toSource()+';var png='+png.toSource()+';var verifyText='+verifyText.toSource()+';var verifyNative='+verifyNative.toSource()+';\n';
            var files=[], batchSize=8,totalBatches=1+Math.ceil((operations.length-staticCount)/batchSize);
            function asciiScript(code) {return code.replace(/[^\x00-\x7F]/g,function(c){return '\\u'+('0000'+c.charCodeAt(0).toString(16)).slice(-4);});}
            for(i=0;i<operations.length;) {
                var end=i===0?staticCount:Math.min(i+batchSize,operations.length), last=end===operations.length;
                var stepFile=new File(steps.fsName+'/'+files.length+'.jsx');stepFile.encoding='UTF-8';stepFile.open('w');
                stepFile.write(asciiScript(worker+'('+drawBatch.toSource()+')('+token.toSource()+','+operations.slice(i,end).toSource()+','+last+','+(last?names.toSource():'[]')+','+expectedPaths+','+expectedTexts+','+end+','+files.length+','+totalBatches+');'));stepFile.close();
                files.push(encodeURI(stepFile.fsName));
                i=end;
            }
            var live=app.documents.add(DocumentColorSpace.RGB,cfg.width,cfg.height);
            live.artboards[0].artboardRect=[0,cfg.height,cfg.width,0];live.layers[0].name=token;
            app.executeMenuCommand('fitin');app.redraw();
            function writeControl(name,value) {var f=new File(cfg.job+'/'+name);f.encoding='UTF-8';f.open('w');f.write(value);f.close();}
            writeControl('live-plan.txt',files.join('\n'));
            writeControl('live-cursor.txt','0');writeControl('live-command.txt','pause');
            var state={job:cfg.job,closed:false};
            var old=$.global.looonLivePanel;if(old && !old.closed) old.window.close();
            var panel=new Window('palette','Illustrator Live Drawing');panel.orientation='column';
            var status=panel.add('statictext',undefined,'Ready - blank canvas; start the OS runner');status.preferredSize=[400,25];
            var bar=panel.add('progressbar',undefined,0,files.length);bar.preferredSize=[400,12];
            var row=panel.add('group'), start=row.add('button',undefined,'Start / Resume'), pause=row.add('button',undefined,'Pause'), step=row.add('button',undefined,'Step');
            start.onClick=function(){writeControl('live-command.txt','play');status.text='Playing - see canvas';record('PLAY');};
            pause.onClick=function(){writeControl('live-command.txt','pause');status.text='Paused after the current batch';record('PAUSE');};
            step.onClick=function(){writeControl('live-command.txt','step');status.text='Step requested';record('STEP');};
            panel.onClose=function(){writeControl('live-command.txt','stop');state.closed=true;record('CLOSED');};
            state.window=panel;$.global.looonLivePanel=state;panel.show();panel.active=true;
            record('READY - blank canvas; '+files.length+' batches; OS runner required');
            return;
        }
        record('DONE');
    } catch(e) {record('ERROR: '+e+'; line='+e.line);}
    log.close();
}());
