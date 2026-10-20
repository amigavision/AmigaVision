/*
    crt-pi - A Raspberry Pi friendly CRT shader.

    Copyright (C) 2015-2016 davej

    This program is free software; you can redistribute it and/or modify it
    under the terms of the GNU General Public License as published by the Free
    Software Foundation; either version 2 of the License, or (at your option)
    any later version. 

*/	

#define SCANLINE_WEIGHT 6.0
#define SCANLINE_GAP_BRIGHTNESS 0.12
#define BLOOM_FACTOR 1.5
#define BRIGHTBOOST 1.0
#define INPUT_GAMMA 2.4
#define OUTPUT_GAMMA 2.2 

#define filterWidth 0.125

// Haven't put these as parameters as it would slow the code down.
#define SCANLINES
#define MULTISAMPLE
#define GAMMA
//#define FAKE_GAMMA
//#define SHARPER

	
string name : NAME = "crtpi";

float2 ps1                      : TEXELSIZE;
float2 ir                       : sourcescale;

float4x4 World                  : WORLD;
float4x4 View                   : VIEW;
float4x4 Projection             : PROJECTION;
float4x4 Worldview              : WORLDVIEW;               // world * view
float4x4 ViewProjection         : VIEWPROJECTION;          // view * projection
float4x4 WorldViewProjection    : WORLDVIEWPROJECTION;     // world * view * projection

string combineTechique          : COMBINETECHNIQUE = "CRTPI";

texture SourceTexture	        : SOURCETEXTURE;

sampler	decal = sampler_state
{
	Texture	  = (SourceTexture);
	MinFilter = LINEAR;
	MagFilter = LINEAR;
};


struct out_vertex {
	float4 position : POSITION;
	float4 color    : COLOR;
	float2 t0       : TEXCOORD0;
}; 
 

out_vertex  VS_VERTEX(float3 position : POSITION, float2 texCoord : TEXCOORD0 )
{ 
	out_vertex OUT = (out_vertex)0;

	OUT.position = mul(float4(position,1.0),WorldViewProjection);
	OUT.t0 = texCoord;
	return OUT;  
}

float CalcScanLineWeight(float dist)
{
	return max(1.0-dist*dist*SCANLINE_WEIGHT, SCANLINE_GAP_BRIGHTNESS);
}

float CalcScanLine(float dy)
{
	float scanLineWeight = CalcScanLineWeight(dy);
#if defined(MULTISAMPLE)
	scanLineWeight += CalcScanLineWeight(dy-filterWidth);
	scanLineWeight += CalcScanLineWeight(dy+filterWidth);
	scanLineWeight *= 0.3333333;
#endif
	return scanLineWeight;
} 

float4 PS_FRAGMENT (in out_vertex VAR) : COLOR
{
		float2 tmp = (ir.x < 1.0) ? float2(1.0,1.0) : ir;
		float2 ps = ps1*tmp;
	
		float2 texcoordInPixels = VAR.t0 / ps;
#if defined(SHARPER)
		float2 tempCoord = floor(texcoordInPixels) + 0.5;
		float2 coord = tempCoord * ps;
		float2 deltas = texcoordInPixels - tempCoord;
		float scanLineWeight = CalcScanLine(deltas.y);
		float2 signs = sign(deltas);
		deltas.x *= 2.0;
		deltas = deltas * deltas;
		deltas.y = deltas.y * deltas.y;
		deltas.x *= 0.5;
		deltas.y *= 8.0;
		deltas *= ps;
		deltas *= signs;
		float2 tc = coord + deltas;
#else
		float tempY = floor(texcoordInPixels.y) + 0.5;
		float yCoord = tempY * ps.y;
		float dy = texcoordInPixels.y - tempY;
		float scanLineWeight = CalcScanLine(dy);
		float signY = sign(dy);
		dy = dy * dy;
		dy = dy * dy;
		dy *= 8.0;
		dy *= ps.y;
		dy *= signY;
		float2 tc = float2(VAR.t0.x, yCoord + dy);
#endif

		float3 colour = tex2D(decal, tc).rgb;

#if defined(SCANLINES)
#if defined(GAMMA)
#if defined(FAKE_GAMMA)
		colour = colour * colour;
#else
		colour = pow(colour, float3(INPUT_GAMMA,INPUT_GAMMA,INPUT_GAMMA));
#endif
#endif
		scanLineWeight *= BLOOM_FACTOR;
		colour *= scanLineWeight;

#if defined(GAMMA)
#if defined(FAKE_GAMMA)
		colour = sqrt(colour);
#else
		colour = pow(colour, float3(1.0/OUTPUT_GAMMA,1.0/OUTPUT_GAMMA,1.0/OUTPUT_GAMMA));
#endif
#endif
#endif 	

		return float4(colour*BRIGHTBOOST, 1.0);	
}



technique CRTPI
{
    pass P0
    {
        // shaders		
        VertexShader = compile vs_3_0 VS_VERTEX();
        PixelShader  = compile ps_3_0 PS_FRAGMENT(); 
    }  
}
